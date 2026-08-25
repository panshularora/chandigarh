from __future__ import annotations

import numpy as np
from PIL import Image


def thermal(norm: np.ndarray) -> np.ndarray:
    """Navy → cyan → saffron → paper heat ramp, not the generic rainbow."""
    x = np.clip(norm, 0, 1)
    r = np.zeros_like(x)
    g = np.zeros_like(x)
    b = np.zeros_like(x)
    # 0–0.35 navy/cyan
    m = x <= 0.35
    t = np.where(m, x / 0.35, 0)
    r[m] = 7 + t[m] * 110
    g[m] = 16 + t[m] * 166
    b[m] = 24 + t[m] * 177
    # 0.35–0.7 cyan → saffron
    m = (x > 0.35) & (x <= 0.7)
    t = np.where(m, (x - 0.35) / 0.35, 0)
    r[m] = 117 + t[m] * 81
    g[m] = 182 - t[m] * 92
    b[m] = 201 - t[m] * 175
    # 0.7–1 saffron → paper
    m = x > 0.7
    t = np.where(m, (x - 0.7) / 0.3, 0)
    r[m] = 198 + t[m] * 34
    g[m] = 90 + t[m] * 134
    b[m] = 26 + t[m] * 178
    return np.stack([r, g, b], axis=-1).astype(np.uint8)


def save_heatmap(arr: np.ndarray, dest) -> None:
    if arr.size == 0:
        Image.new("RGB", (8, 8), (7, 16, 24)).save(dest)
        return
    a = arr.astype(np.float32)
    a = a - a.min()
    peak = float(a.max()) or 1.0
    a = a / peak
    img = Image.fromarray(thermal(a), "RGB")
    img.save(dest, "PNG")


def overlay_on(original: Image.Image, heat: np.ndarray, alpha: float = 0.48) -> Image.Image:
    base = original.convert("RGB")
    if heat.size == 0:
        return base
    h = heat.astype(np.float32)
    h = h - h.min()
    peak = float(h.max()) or 1.0
    h = h / peak
    therm = Image.fromarray(thermal(h), "RGB").resize(base.size, Image.Resampling.BILINEAR)
    mask = Image.fromarray((np.clip(h, 0, 1) * 255 * alpha).astype(np.uint8), "L").resize(
        base.size, Image.Resampling.BILINEAR
    )
    return Image.composite(therm, base, mask)
