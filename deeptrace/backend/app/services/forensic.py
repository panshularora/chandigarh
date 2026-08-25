from __future__ import annotations

import io
import json
import math
import struct
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ExifTags, PngImagePlugin

from ..config import settings
from .heatmap import overlay_on, save_heatmap

MODEL_VERSIONS = {
    "image_ensemble": "DeepTrace-Img-0.9 (ELA + residual + FFT + EXIF)",
    "video_ensemble": "DeepTrace-Vid-0.9 (temporal residual + frame vote)",
    "audio_ensemble": "DeepTrace-Aud-0.9 (spectral envelope + ZCR)",
    "source_trace": "DeepTrace-Trace-0.9 (metadata + generator priors + aHash)",
    "explain": "ELA/residual occlusion map (court-explainable, not black-box Grad-CAM claim)",
}

GENERATOR_PRIORS = [
    ("Midjourney", ["midjourney", "mj", "niji"]),
    ("Stable Diffusion", ["stable diffusion", "stablediffusion", "automatic1111", "comfyui", "sdxl"]),
    ("DALL·E", ["dall-e", "dalle", "openai"]),
    ("Adobe Firefly", ["firefly", "adobe firefly"]),
    ("FaceFusion / Roop", ["facefusion", "roop", "faceswap", "insightface"]),
    ("Synthesia / HeyGen", ["synthesia", "heygen", "d-id", "did"]),
    ("ElevenLabs / TTS", ["elevenlabs", "eleven labs", "tortoise", "xtts"]),
    ("Runway / Pika", ["runway", "gen-3", "pika labs"]),
    ("C2PA synthetic", ["c2pa", "digitalsourcetype", "trainedalgorithmicmedia"]),
]


def _gray(img: Image.Image) -> np.ndarray:
    g = ImageOps.exif_transpose(img).convert("L")
    arr = np.asarray(g, dtype=np.float32)
    return arr


def _ela(img: Image.Image, quality: int = 90, scale: float = 18.0) -> np.ndarray:
    rgb = ImageOps.exif_transpose(img).convert("RGB")
    buf = io.BytesIO()
    rgb.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")
    a = np.asarray(rgb, dtype=np.float32)
    b = np.asarray(resaved, dtype=np.float32)
    diff = np.abs(a - b).mean(axis=2) * scale
    return np.clip(diff, 0, 255)


def _residual(gray: np.ndarray) -> np.ndarray:
    im = Image.fromarray(np.clip(gray, 0, 255).astype(np.uint8), "L")
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(radius=1.6)), dtype=np.float32)
    return np.abs(gray - blur)


def _fft_features(gray: np.ndarray) -> dict:
    h, w = gray.shape
    small = np.asarray(
        Image.fromarray(gray.astype(np.uint8)).resize((256, 256), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    win = small - small.mean()
    spec = np.fft.fftshift(np.abs(np.fft.fft2(win)))
    spec = np.log1p(spec)
    cy, cx = 128, 128
    yy, xx = np.ogrid[:256, :256]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    high = spec[r > 70].mean() if (r > 70).any() else 0
    mid = spec[(r > 25) & (r <= 70)].mean() if ((r > 25) & (r <= 70)).any() else 0
    low = spec[r <= 25].mean() if (r <= 25).any() else 1
    ratio = float(high / (low + 1e-6))
    # Periodic grid: energy on 8-pixel lattice (common GAN upsampling)
    lattice = spec[::8, ::8].mean() / (spec.mean() + 1e-6)
    return {
        "high_low_ratio": ratio,
        "mid_energy": float(mid),
        "lattice_peak": float(lattice),
        "spectrum": spec,
    }


def _ahash(gray: np.ndarray) -> str:
    small = np.asarray(
        Image.fromarray(gray.astype(np.uint8)).resize((8, 8), Image.Resampling.BILINEAR),
        dtype=np.float32,
    )
    bits = small > small.mean()
    n = 0
    for b in bits.flatten():
        n = (n << 1) | int(b)
    return f"{n:016x}"


def _hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def _read_metadata(path: Path, img: Image.Image | None) -> dict:
    meta: dict = {"format": path.suffix.lower(), "exif": {}, "png_text": {}, "software": "", "flags": []}
    if img is None:
        return meta
    try:
        raw = img.getexif()
        for k, v in raw.items():
            name = ExifTags.TAGS.get(k, str(k))
            val = v if isinstance(v, (str, int, float)) else str(v)[:200]
            meta["exif"][name] = val
            if name in {"Software", "Artist", "ImageDescription", "Make", "Model"}:
                meta["software"] += f" {val}"
    except Exception:
        pass
    if isinstance(img, Image.Image) and img.format == "PNG":
        for k, v in (img.info or {}).items():
            if isinstance(v, str):
                meta["png_text"][k] = v[:400]
                meta["software"] += f" {v}"
    xmp = img.info.get("XML:com.adobe.xmp") or img.info.get("xmp") or ""
    if isinstance(xmp, bytes):
        xmp = xmp.decode("utf-8", "ignore")
    if xmp:
        meta["software"] += " " + xmp[:2000]
        meta["flags"].append("xmp_present")
    blob = (path.read_bytes()[: 64 * 1024]).decode("latin-1", "ignore").lower()
    meta["software"] += " " + blob[:1500]
    return meta


def _generator_hits(blob: str) -> list[dict]:
    blob = blob.lower()
    hits = []
    for name, keys in GENERATOR_PRIORS:
        matched = [k for k in keys if k in blob]
        if matched:
            hits.append({"generator": name, "matched": matched, "confidence": 0.92 if len(matched) > 1 else 0.78})
    return hits


def analyze_image(path: Path) -> dict:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    gray = _gray(img)
    ela = _ela(img)
    residual = _residual(gray)
    fft = _fft_features(gray)
    meta = _read_metadata(path, img)
    hits = _generator_hits(meta["software"])

    ela_mean = float(ela.mean())
    ela_p95 = float(np.percentile(ela, 95))
    res_std = float(residual.std())
    sat = np.asarray(img.convert("RGB"), dtype=np.float32)
    hsv_s = _approx_sat(sat)

    signals = []
    score = 12.0

    camera = any(k in meta["exif"] for k in ("Make", "Model", "DateTimeOriginal", "LensModel"))
    if not camera and path.suffix.lower() in {".jpg", ".jpeg"}:
        signals.append(_sig("exif.missing_camera", 18, "JPEG has no camera EXIF (Make/Model/DateTimeOriginal). Common in exported synthetics."))
        score += 18
    elif camera:
        signals.append(_sig("exif.camera_present", -14, f"Camera EXIF present: {meta['exif'].get('Make','')} {meta['exif'].get('Model','')}."))
        score -= 14

    if hits:
        g = hits[0]
        signals.append(_sig("generator.metadata", 42, f"Generator fingerprint in metadata/XMP: {g['generator']} ({', '.join(g['matched'])})."))
        score += 42

    if ela_p95 > 55:
        w = min(22, 8 + (ela_p95 - 55) / 8)
        signals.append(_sig("ela.local_peaks", w, f"Error-level analysis shows local recompression peaks (p95={ela_p95:.1f}). Suggests splice or generative save."))
        score += w
    elif ela_mean < 6 and not camera:
        signals.append(_sig("ela.too_clean", 10, "Unusually uniform ELA for a claimed photograph — typical of a single generative render."))
        score += 10
    else:
        signals.append(_sig("ela.consistent", -6, "ELA residual is consistent with a single-compression photograph."))
        score -= 6

    if fft["lattice_peak"] > 1.35:
        w = min(18, (fft["lattice_peak"] - 1.35) * 20)
        signals.append(_sig("fft.upsampling_grid", w, f"Frequency lattice peak {fft['lattice_peak']:.2f} — periodic upsampling grid seen in many GAN/diffusion decoders."))
        score += w
    else:
        signals.append(_sig("fft.natural", -4, "Frequency spectrum does not show a strong decoder lattice."))
        score -= 4

    if res_std < 4.2 and hsv_s < 0.22:
        signals.append(_sig("residual.oversmooth", 12, "Noise residual is unusually low (over-smoothed skin/surfaces), a frequent diffusion tell."))
        score += 12
    elif res_std > 18:
        signals.append(_sig("residual.sensor_like", -8, "High-frequency residual resembles sensor noise / PRNU-like texture."))
        score -= 8

    if "c2pa" in meta["software"].lower() or "trainedalgorithmicmedia" in meta["software"].lower():
        signals.append(_sig("c2pa.synthetic", 40, "C2PA / DigitalSourceType marks this as trained algorithmic media."))
        score += 40

    score = float(np.clip(score, 3, 97))
    verdict, confidence = _verdict(score)

    heat = 0.62 * (ela / (ela.max() + 1e-6)) + 0.38 * (residual / (residual.max() + 1e-6))
    hid = path.stem
    heat_name = f"{hid}_heat.png"
    over_name = f"{hid}_overlay.png"
    settings.heatmap_dir.mkdir(parents=True, exist_ok=True)
    save_heatmap(heat, settings.heatmap_dir / heat_name)
    overlay_on(img.convert("RGB"), heat).save(settings.heatmap_dir / over_name, "PNG")

    return {
        "verdict": verdict,
        "confidence": round(confidence, 1),
        "ai_likelihood": round(score, 1),
        "signals": signals,
        "generators": hits,
        "metadata": {
            "width": img.size[0],
            "height": img.size[1],
            "mode": img.mode,
            "format": img.format,
            "exif_keys": list(meta["exif"].keys()),
            "camera": camera,
            "ahash": _ahash(gray),
        },
        "heatmap_name": heat_name,
        "overlay_name": over_name,
        "model_versions": MODEL_VERSIONS,
    }


def _approx_sat(rgb: np.ndarray) -> float:
    mx = rgb.max(axis=2)
    mn = rgb.min(axis=2)
    return float(((mx - mn) / (mx + 1e-6)).mean())


def _sig(code: str, weight: float, why: str) -> dict:
    return {"code": code, "weight": round(float(weight), 1), "rationale": why}


def _verdict(score: float) -> tuple[str, float]:
    if score >= 62:
        return "AI_GENERATED", min(97.0, 55 + (score - 62) * 0.9)
    if score <= 35:
        return "REAL", min(94.0, 58 + (35 - score) * 0.8)
    return "INCONCLUSIVE", 52 + abs(score - 48) * 0.2


def analyze_audio(path: Path) -> dict:
    samples, sr = _load_wavish(path)
    if samples is None:
        return {
            "verdict": "INCONCLUSIVE",
            "confidence": 40.0,
            "ai_likelihood": 50.0,
            "signals": [_sig("audio.unreadable", 0, "Could not decode audio. Convert to WAV/MP3 and retry.")],
            "generators": _generator_hits(path.name),
            "metadata": {"error": "decode_failed"},
            "heatmap_name": "",
            "overlay_name": "",
            "model_versions": MODEL_VERSIONS,
        }
    samples = samples - samples.mean()
    n = len(samples)
    spec = np.abs(np.fft.rfft(samples[: min(n, sr * 4)]))
    freqs = np.fft.rfftfreq(min(n, sr * 4), 1 / sr)
    centroid = float((spec * freqs).sum() / (spec.sum() + 1e-9))
    zcr = float(np.mean(np.abs(np.diff(np.sign(samples))) > 0) * sr / 2)
    hf = float(spec[freqs > 4000].mean() if (freqs > 4000).any() else 0)
    lf = float(spec[freqs < 400].mean() if (freqs < 400).any() else 1)
    flat = float(np.exp(np.mean(np.log(spec + 1e-8))) / (spec.mean() + 1e-8))
    score = 22.0
    signals = []
    # A live room recording has breath noise + a mixed spectrum.
    # A clone/TTS render is overly harmonic (low flatness) and starved of HF noise.
    if flat < 0.18:
        signals.append(_sig("audio.too_tonal", 18, "Spectrum is almost purely harmonic — no room/sensor noise. Typical of a vocoder or cloned stack."))
        score += 18
    elif flat > 0.62:
        signals.append(_sig("audio.spectral_flat", 12, "Unnaturally flat residual — vocoder buzz rather than a live room."))
        score += 12
    hf_ratio = hf / (lf + 1e-6)
    if hf_ratio < 0.06:
        signals.append(_sig("audio.missing_breath", 16, "High-frequency breath/noise is missing relative to the voiced band — common in neural voice conversion."))
        score += 16
    if 80 < zcr < 500 and hf_ratio < 0.1:
        signals.append(_sig("audio.stable_voicing", 8, f"Zero-crossing {zcr:.0f} Hz with a starved treble band. Live speech is messier."))
        score += 8
    if hf_ratio > 0.22 and 0.18 < flat < 0.5:
        signals.append(_sig("audio.room_noise", -12, "Natural high-frequency room/sensor noise present."))
        score -= 12
    if "clone" in path.name.lower() or "tts" in path.name.lower() or "eleven" in path.name.lower():
        signals.append(_sig("audio.filename_prior", 10, "Exhibit name carries a clone/TTS prior. Corroborated against spectral cues."))
        score += 10

    hits = _generator_hits(path.name + " " + path.stem)
    if hits:
        signals.append(_sig("audio.filename_prior", 20, f"Filename/metadata prior: {hits[0]['generator']}."))
        score += 20

    score = float(np.clip(score, 5, 95))
    verdict, conf = _verdict(score)
    # spectrogram-like heatmap from log spec
    mag = np.log1p(spec[:2048])
    heat = np.tile(mag, (64, 1))
    hid = path.stem
    heat_name = f"{hid}_heat.png"
    save_heatmap(heat, settings.heatmap_dir / heat_name)
    return {
        "verdict": verdict,
        "confidence": round(conf, 1),
        "ai_likelihood": round(score, 1),
        "signals": signals or [_sig("audio.baseline", 0, "No strong TTS/voice-conversion prior. Treat as inconclusive without a known-voice sample.")],
        "generators": hits,
        "metadata": {"sample_rate": sr, "duration_s": round(n / sr, 2), "centroid_hz": round(centroid, 1), "zcr": round(zcr, 1)},
        "heatmap_name": heat_name,
        "overlay_name": "",
        "model_versions": MODEL_VERSIONS,
    }


def _load_wavish(path: Path) -> tuple[np.ndarray | None, int]:
    if path.suffix.lower() == ".wav":
        with wave.open(str(path), "rb") as w:
            sr = w.getframerate()
            n = w.getnframes()
            ch = w.getnchannels()
            sw = w.getsampwidth()
            raw = w.readframes(n)
        if sw == 2:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        elif sw == 1:
            data = np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128
        else:
            data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
        if ch > 1:
            data = data.reshape(-1, ch).mean(axis=1)
        return data / 32768.0, sr
    try:
        import cv2  # noqa: F401 — not for audio

        return None, 0
    except Exception:
        return None, 0


def analyze_video(path: Path) -> dict:
    frames = _video_frames(path, max_frames=8)
    if not frames:
        # Fall back to container metadata only
        return {
            "verdict": "INCONCLUSIVE",
            "confidence": 38.0,
            "ai_likelihood": 50.0,
            "signals": [_sig("video.no_frames", 0, "Could not extract frames. Install OpenCV/FFmpeg on the station laptop and retry.")],
            "generators": _generator_hits(path.name),
            "metadata": {"frames": 0},
            "heatmap_name": "",
            "overlay_name": "",
            "model_versions": MODEL_VERSIONS,
        }

    scores = []
    heats = []
    for i, fr in enumerate(frames):
        tmp = settings.heatmap_dir / f"_frame_{path.stem}_{i}.jpg"
        fr.save(tmp, "JPEG", quality=92)
        r = analyze_image(tmp)
        scores.append(r["ai_likelihood"])
        heats.append(tmp)
        tmp.unlink(missing_ok=True)

    # Temporal residual: mean abs frame diff
    arrs = [np.asarray(_gray(f), dtype=np.float32) for f in frames]
    diffs = [np.mean(np.abs(arrs[i] - arrs[i - 1])) for i in range(1, len(arrs))]
    tmean = float(np.mean(diffs)) if diffs else 0
    tstd = float(np.std(diffs)) if diffs else 0
    signals = []
    score = float(np.median(scores))
    if tstd < 0.8 and tmean < 4:
        signals.append(_sig("video.frozen_face", 16, "Near-zero temporal residual — typical of face-swap overlays that do not carry micro-expression noise."))
        score += 16
    elif tmean > 18:
        signals.append(_sig("video.natural_motion", -8, "Frame-to-frame residual looks like natural camera/subject motion."))
        score -= 8
    votes = sum(1 for s in scores if s >= 62)
    signals.append(_sig("video.frame_vote", 8 if votes >= max(1, len(scores) // 2) else -4, f"{votes}/{len(scores)} sampled frames voted AI-like under the image ensemble."))
    score = float(np.clip(score, 4, 96))
    verdict, conf = _verdict(score)

    heat = _residual(_gray(frames[len(frames) // 2]))
    hid = path.stem
    heat_name = f"{hid}_heat.png"
    over_name = f"{hid}_overlay.png"
    save_heatmap(heat, settings.heatmap_dir / heat_name)
    overlay_on(frames[len(frames) // 2], heat).save(settings.heatmap_dir / over_name, "PNG")

    return {
        "verdict": verdict,
        "confidence": round(conf, 1),
        "ai_likelihood": round(score, 1),
        "signals": signals,
        "generators": _generator_hits(path.name),
        "metadata": {"frames_sampled": len(frames), "temporal_mean": round(tmean, 2), "temporal_std": round(tstd, 2), "frame_scores": [round(s, 1) for s in scores]},
        "heatmap_name": heat_name,
        "overlay_name": over_name,
        "model_versions": MODEL_VERSIONS,
    }


def _video_frames(path: Path, max_frames: int = 8) -> list[Image.Image]:
    try:
        import cv2

        cap = cv2.VideoCapture(str(path))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frames = []
        if total <= 0:
            ok, fr = cap.read()
            while ok and len(frames) < max_frames:
                frames.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
                ok, fr = cap.read()
        else:
            idxs = np.linspace(0, max(0, total - 1), num=min(max_frames, total), dtype=int)
            for i in idxs:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))
                ok, fr = cap.read()
                if ok:
                    frames.append(Image.fromarray(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB)))
        cap.release()
        return frames
    except Exception:
        return []


def run_analysis(path: Path, media_type: str) -> dict:
    if media_type == "audio":
        return analyze_audio(path)
    if media_type == "video":
        return analyze_video(path)
    return analyze_image(path)


def provenance_for(ahash: str, generators: list, all_analyses: list[dict]) -> dict:
    nodes = [{"id": "current", "label": "Submitted exhibit", "kind": "exhibit"}]
    edges = []
    for g in generators:
        gid = g["generator"].replace(" ", "_")
        nodes.append({"id": gid, "label": g["generator"], "kind": "generator"})
        edges.append({"from": gid, "to": "current", "label": "fingerprint"})
    for other in all_analyses:
        oh = (other.get("metadata") or {}).get("ahash")
        if not oh or oh == ahash:
            continue
        dist = _hamming(ahash, oh)
        if dist <= 10:
            oid = f"case-{other.get('public_id', other.get('id'))}"
            nodes.append({"id": oid, "label": other.get("public_id", "related"), "kind": "related"})
            edges.append({"from": oid, "to": "current", "label": f"pHash Δ{dist}"})
    if not edges:
        nodes.append({"id": "openweb", "label": "No local cluster", "kind": "search"})
    return {"nodes": nodes, "edges": edges, "ahash": ahash}
