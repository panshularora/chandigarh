from __future__ import annotations

import io
import json
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import Analysis, Case, Evidence, Operator, Report
from .security import hash_password
from .services.custody import append_event
from .services.forensic import run_analysis, provenance_for
from .services.storage import hashes_of, save_upload, ensure_dirs, upload_path


def _exif_img(kind: str) -> bytes:
    rng = np.random.default_rng(7 if kind == "real" else 99)
    if kind == "real":
        y, x = np.mgrid[0:720, 0:960]
        base = 90 + 40 * np.sin(x / 70.0) + 28 * np.cos(y / 55.0)
        noise = rng.normal(0, 11, base.shape)
        rgb = np.stack(
            [
                np.clip(base + noise + 18, 0, 255),
                np.clip(base * 0.92 + noise + 8, 0, 255),
                np.clip(base * 0.7 + noise * 1.1, 0, 255),
            ],
            axis=-1,
        ).astype(np.uint8)
        img = Image.fromarray(rgb, "RGB")
        draw = ImageDraw.Draw(img)
        draw.rectangle((40, 520, 920, 700), fill=(28, 36, 48))
        draw.text((60, 540), "SECTOR 17  ·  CCTV STILL  ·  14:22 IST", fill=(232, 224, 204))
        draw.text((60, 575), "Chandigarh Police  ·  original export", fill=(126, 182, 201))
        exif = Image.Exif()
        exif[271] = "Canon"
        exif[272] = "EOS 90D"
        exif[306] = "2026:03:11 14:22:08"
        exif[36867] = "2026:03:11 14:22:08"
        exif[305] = "Canon EOS Firmware"
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=91, exif=exif)
        return buf.getvalue()

    # Synthetic: over-smooth portrait-ish oval + Midjourney tag
    img = Image.new("RGB", (768, 960), (18, 22, 28))
    d = ImageDraw.Draw(img)
    d.ellipse((160, 80, 608, 620), fill=(196, 154, 128))
    d.ellipse((250, 220, 340, 300), fill=(40, 48, 58))
    d.ellipse((430, 220, 520, 300), fill=(40, 48, 58))
    d.ellipse((330, 360, 440, 410), fill=(150, 90, 90))
    img = img.filter(ImageFilter.GaussianBlur(2.4))
    arr = np.asarray(img).astype(np.float32)
    arr += rng.normal(0, 1.4, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(img)
    d.rectangle((0, 860, 768, 960), fill=(12, 16, 22))
    d.text((24, 890), "FaceFusion export  ·  digital-arrest call still", fill=(198, 90, 26))
    exif = Image.Exif()
    exif[305] = "Midjourney / FaceFusion 2.6"
    exif[270] = "trainedAlgorithmicMedia"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, exif=exif)
    return buf.getvalue()


def _wav(kind: str) -> bytes:
    sr = 16000
    t = np.linspace(0, 3.2, int(sr * 3.2), endpoint=False)
    if kind == "clone":
        # Harmonic stack, no breath — TTS-like
        sig = 0.28 * np.sin(2 * np.pi * 140 * t)
        for k, a in enumerate([0.18, 0.12, 0.08, 0.05], start=2):
            sig += a * np.sin(2 * np.pi * 140 * k * t)
        env = 0.5 + 0.5 * np.sin(2 * np.pi * 3.2 * t)
        sig *= env
    else:
        rng = np.random.default_rng(3)
        sig = 0.15 * np.sin(2 * np.pi * 180 * t)
        sig += 0.08 * rng.normal(0, 1, t.shape)
        sig += 0.04 * np.sin(2 * np.pi * 2400 * t) * rng.random(t.shape)
    pcm = np.clip(sig * 32767, -32767, 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def seed_if_empty() -> None:
    ensure_dirs()
    db: Session = SessionLocal()
    try:
        if db.query(Operator).count():
            return
        ops = [
            Operator(
                username="inspector",
                full_name="Insp. Navneet Kaur",
                role="inspector",
                station="Cyber Cell, Chandigarh",
                badge_no="CHD-CYB-118",
                language="en",
                password_hash=hash_password("chandigarh2026"),
            ),
            Operator(
                username="sp.cyber",
                full_name="SP Cyber  ·  UT Chandigarh",
                role="sp",
                station="PHQ Sector 9, Chandigarh",
                badge_no="CHD-SP-CYB",
                language="en",
                password_hash=hash_password("chandigarh2026"),
            ),
            Operator(
                username="analyst",
                full_name="ASI Rohan Mehta",
                role="analyst",
                station="Cyber Cell, Chandigarh",
                badge_no="CHD-CYB-204",
                language="hi",
                password_hash=hash_password("chandigarh2026"),
            ),
        ]
        db.add_all(ops)
        db.flush()
        inspector = ops[0]

        specs = [
            dict(
                title="Digital-arrest video-call impersonating CBI",
                offence="digital_arrest",
                fir="FIR 41/2026",
                priority="P1",
                summary="Victim in Sector 22 kept on a FaceTime-like call for 7 hours. Caller claimed CBI rank, demanded transfer to mule accounts. Exhibit is a screen-grab from the call.",
                filename="digital_arrest_still.jpg",
                kind="image",
                blob=_exif_img("synth"),
            ),
            dict(
                title="Extortion — synthetic intimate image",
                offence="blackmail",
                fir="GD 1182/2026",
                priority="P1",
                summary="Complainant from Manimajra received a generated image used for blackmail. No original camera file produced by accused.",
                filename="blackmail_synthetic.jpg",
                kind="image",
                blob=_exif_img("synth"),
            ),
            dict(
                title="Investment-scam voice clone of relative",
                offence="investment_scam",
                fir="FIR 56/2026",
                priority="P2",
                summary="Elderly victim in Sector 35 transferred ₹4.8 lakh after a WhatsApp voice note that sounded like her nephew. Audio exhibit attached.",
                filename="nephew_clone.wav",
                kind="audio",
                blob=_wav("clone"),
            ),
            dict(
                title="Planted CCTV still — Sector 17 market",
                offence="planted_evidence",
                fir="FIR 62/2026",
                priority="P2",
                summary="Defence claims the CCTV still annexed to a theft FIR is camera-original. Needs authenticity check before charge-sheet.",
                filename="sector17_cctv.jpg",
                kind="image",
                blob=_exif_img("real"),
            ),
        ]

        for i, spec in enumerate(specs):
            c = Case(
                public_id=f"DT-CHD-2026-{441 + i:05d}",
                fir_number=spec["fir"],
                title=spec["title"],
                offence_type=spec["offence"],
                station="Cyber Cell, Chandigarh",
                status="open",
                priority=spec["priority"],
                summary=spec["summary"],
                created_by=inspector.id,
            )
            db.add(c)
            db.flush()
            append_event(db, case_id=c.id, operator_id=inspector.id, action="CASE_OPENED", detail=spec["title"])
            suffix = Path(spec["filename"]).suffix
            stored = save_upload(spec["blob"], suffix)
            sha256, sha1 = hashes_of(spec["blob"])
            ev = Evidence(
                case_id=c.id,
                filename=spec["filename"],
                stored_name=stored,
                media_type=spec["kind"],
                mime="image/jpeg" if spec["kind"] == "image" else "audio/wav",
                sha256=sha256,
                sha1=sha1,
                size_bytes=len(spec["blob"]),
                uploaded_by=inspector.id,
            )
            db.add(ev)
            db.flush()
            append_event(
                db,
                case_id=c.id,
                operator_id=inspector.id,
                action="EVIDENCE_INGESTED",
                detail=f"{spec['filename']}  SHA-256 {sha256[:16]}…",
                evidence_id=ev.id,
            )
            result = run_analysis(upload_path(stored), spec["kind"])
            result["provenance"] = provenance_for((result.get("metadata") or {}).get("ahash", ""), result.get("generators") or [], [])
            a = Analysis(
                case_id=c.id,
                evidence_id=ev.id,
                operator_id=inspector.id,
                status="complete",
                verdict=result["verdict"],
                confidence=result["confidence"],
                ai_likelihood=result["ai_likelihood"],
                signals_json=json.dumps(result.get("signals") or []),
                generators_json=json.dumps(result.get("generators") or []),
                provenance_json=json.dumps(result.get("provenance") or {}),
                metadata_json=json.dumps(result.get("metadata") or {}),
                heatmap_name=result.get("heatmap_name") or "",
                overlay_name=result.get("overlay_name") or "",
                briefing="",
                model_versions=json.dumps(result.get("model_versions") or {}),
            )
            db.add(a)
            c.status = "analyzed"
            append_event(
                db,
                case_id=c.id,
                operator_id=inspector.id,
                action="ANALYSIS_COMPLETE",
                detail=f"{result['verdict']}  conf {result['confidence']}%",
                evidence_id=ev.id,
            )
        db.commit()
    finally:
        db.close()


def _tiny_video() -> bytes | None:
    try:
        import cv2
    except Exception:
        return None
    path = settings.upload_dir / "_seed_clip.avi"
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 8, (320, 240))
    if not writer.isOpened():
        return None
    rng = np.random.default_rng(4)
    for i in range(20):
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:, :] = (22, 28, 36)
        cv2.ellipse(frame, (160, 110), (72, 92), 0, 0, 360, (196, 154, 128), -1)
        cv2.circle(frame, (138 + (i % 3), 98), 9, (40, 48, 58), -1)
        cv2.circle(frame, (182 - (i % 3), 98), 9, (40, 48, 58), -1)
        frame = np.clip(frame.astype(np.float32) + rng.normal(0, 1.2, frame.shape), 0, 255).astype(np.uint8)
        writer.write(frame)
    writer.release()
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data if len(data) > 1000 else None


def enrich_demo() -> None:
    """Fill briefings, signed PDFs, and a video exhibit on an existing station DB."""
    from .serialize import analysis_out, case_out, custody_out, evidence_out, op_out
    from .services.briefing import local_briefing
    from .services.report_pdf import build_report
    from .models import CustodyEvent

    db: Session = SessionLocal()
    try:
        inspector = db.query(Operator).filter_by(username="inspector").first()
        if not inspector:
            return
        ready = (
            db.query(Evidence).filter_by(media_type="video").count() > 0
            and db.query(Report).count() >= 3
            and db.query(Analysis).filter(Analysis.briefing != "").count() > 0
        )
        if ready:
            return
        analyses = db.query(Analysis).order_by(Analysis.id.asc()).all()
        for a in analyses:
            if a.briefing:
                continue
            ev = db.get(Evidence, a.evidence_id)
            case = db.get(Case, a.case_id)
            a.briefing = local_briefing(case_out(case), analysis_out(a), evidence_out(ev))
        db.commit()

        if db.query(Evidence).filter_by(media_type="video").count() == 0:
            blob = _tiny_video()
            case = db.query(Case).filter_by(offence_type="digital_arrest").first()
            if blob and case:
                stored = save_upload(blob, ".avi")
                sha256, sha1 = hashes_of(blob)
                ev = Evidence(
                    case_id=case.id,
                    filename="cbi_call_clip.avi",
                    stored_name=stored,
                    media_type="video",
                    mime="video/x-msvideo",
                    sha256=sha256,
                    sha1=sha1,
                    size_bytes=len(blob),
                    uploaded_by=inspector.id,
                )
                db.add(ev)
                db.flush()
                append_event(
                    db,
                    case_id=case.id,
                    operator_id=inspector.id,
                    action="EVIDENCE_INGESTED",
                    detail=f"cbi_call_clip.avi  SHA-256 {sha256[:16]}…",
                    evidence_id=ev.id,
                )
                result = run_analysis(upload_path(stored), "video")
                result["provenance"] = provenance_for((result.get("metadata") or {}).get("ahash", ""), result.get("generators") or [], [])
                a = Analysis(
                    case_id=case.id,
                    evidence_id=ev.id,
                    operator_id=inspector.id,
                    status="complete",
                    verdict=result["verdict"],
                    confidence=result["confidence"],
                    ai_likelihood=result["ai_likelihood"],
                    signals_json=json.dumps(result.get("signals") or []),
                    generators_json=json.dumps(result.get("generators") or []),
                    provenance_json=json.dumps(result.get("provenance") or {}),
                    metadata_json=json.dumps(result.get("metadata") or {}),
                    heatmap_name=result.get("heatmap_name") or "",
                    overlay_name=result.get("overlay_name") or "",
                    briefing=local_briefing(case_out(case), result, {"filename": ev.filename, "sha256": sha256}),
                    model_versions=json.dumps(result.get("model_versions") or {}),
                )
                db.add(a)
                append_event(
                    db,
                    case_id=case.id,
                    operator_id=inspector.id,
                    action="ANALYSIS_COMPLETE",
                    detail=f"{result['verdict']}  conf {result['confidence']}%",
                    evidence_id=ev.id,
                )
                db.commit()

        if db.query(Report).count() >= 3:
            return
        ops = {o.id: o for o in db.query(Operator).all()}
        for a in db.query(Analysis).order_by(Analysis.id.asc()).limit(4).all():
            if db.query(Report).filter_by(analysis_id=a.id).first():
                continue
            ev = db.get(Evidence, a.evidence_id)
            case = db.get(Case, a.case_id)
            custody = db.query(CustodyEvent).filter(CustodyEvent.case_id == case.id).order_by(CustodyEvent.id.asc()).all()
            fname = f"{case.public_id}_{a.id}.pdf"
            dest = settings.report_dir / fname
            sealed = build_report(
                dest=dest,
                case=case_out(case),
                evidence=evidence_out(ev),
                analysis=analysis_out(a),
                custody=[custody_out(e, ops) for e in custody],
                operator=op_out(inspector),
            )
            db.add(
                Report(
                    case_id=case.id,
                    analysis_id=a.id,
                    filename=fname,
                    content_hash=sealed["content_hash"],
                    signature=sealed["signature"],
                    generated_by=inspector.id,
                )
            )
            case.status = "reported"
            append_event(
                db,
                case_id=case.id,
                operator_id=inspector.id,
                action="REPORT_SIGNED",
                detail=f"HMAC {sealed['signature'][:16]}…",
                evidence_id=ev.id,
            )
        db.commit()
    finally:
        db.close()
