from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib.colors import Color, HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from ..config import settings

NAVY = HexColor("#071018")
STEEL = HexColor("#13202C")
CYAN = HexColor("#7EB6C9")
PAPER = HexColor("#E8E0CC")
SAFFRON = HexColor("#C65A1A")
INK = HexColor("#12141A")
MUTED = HexColor("#5C6570")
RED = HexColor("#C4312B")
GREEN = HexColor("#2F8F6A")


def _verdict_color(v: str) -> Color:
    if v == "AI_GENERATED":
        return RED
    if v == "REAL":
        return GREEN
    return SAFFRON


def report_payload(case: dict, evidence: dict, analysis: dict) -> str:
    return f"{case['public_id']}|{evidence.get('sha256')}|{analysis['verdict']}|{analysis['ai_likelihood']}"


def sign_payload(payload: str) -> str:
    return hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()


def verify_signature(payload: str, signature: str) -> bool:
    return hmac.compare_digest(sign_payload(payload), signature)


def build_report(
    *,
    dest: Path,
    case: dict,
    evidence: dict,
    analysis: dict,
    custody: list[dict],
    operator: dict,
) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(dest), pagesize=A4)
    w, h = A4

    c.setFillColor(NAVY)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(STEEL)
    c.rect(0, h - 28 * mm, w, 28 * mm, fill=1, stroke=0)
    c.setFillColor(SAFFRON)
    c.rect(0, h - 28 * mm, 3 * mm, 28 * mm, fill=1, stroke=0)

    c.setFillColor(PAPER)
    c.setFont("Times-Bold", 16)
    c.drawString(12 * mm, h - 12 * mm, "DEEPTRACE")
    c.setFont("Helvetica", 8)
    c.setFillColor(CYAN)
    c.drawString(12 * mm, h - 17 * mm, "AI-GENERATED MEDIA DETECTION & SOURCE TRACING")
    c.setFillColor(PAPER)
    c.setFont("Helvetica", 8)
    c.drawRightString(w - 12 * mm, h - 12 * mm, "Chandigarh Police  ·  Cyber Cell")
    c.drawRightString(w - 12 * mm, h - 17 * mm, "FIR annexure  ·  Bharatiya Sakshya Adhiniyam, 2023  s.63")
    c.setFont("Helvetica", 7)
    c.setFillColor(MUTED)
    c.drawString(12 * mm, h - 24 * mm, f"Exhibit report  {case['public_id']}  ·  generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    y = h - 38 * mm
    c.setFillColor(PAPER)
    c.setFont("Times-Bold", 13)
    c.drawString(12 * mm, y, "Forensic authenticity report")
    y -= 8 * mm

    rows = [
        ("Case ID", case["public_id"]),
        ("FIR / GD", case.get("fir_number") or "—"),
        ("Offence", case.get("offence_type", "").replace("_", " ").title()),
        ("Station", case.get("station", "")),
        ("Exhibit", evidence.get("filename", "")),
        ("SHA-256", evidence.get("sha256", "")),
        ("Media", evidence.get("media_type", "")),
        ("Operator", f"{operator.get('full_name')}  ({operator.get('badge_no')})"),
        ("Model pack", "DeepTrace ensemble 0.9  ·  ONNX-ready"),
    ]
    c.setFont("Helvetica", 8)
    for label, value in rows:
        c.setFillColor(CYAN)
        c.drawString(12 * mm, y, label.upper())
        c.setFillColor(PAPER)
        c.setFont("Courier", 8)
        c.drawString(48 * mm, y, str(value)[:92])
        c.setFont("Helvetica", 8)
        y -= 5.2 * mm

    y -= 2 * mm
    vc = _verdict_color(analysis["verdict"])
    c.setFillColor(vc)
    c.roundRect(12 * mm, y - 14 * mm, w - 24 * mm, 18 * mm, 2, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Times-Bold", 14)
    c.drawString(16 * mm, y - 5 * mm, analysis["verdict"].replace("_", " "))
    c.setFont("Helvetica", 9)
    c.drawString(16 * mm, y - 11 * mm, f"Calibrated confidence {analysis['confidence']}%    ·    AI-likelihood {analysis['ai_likelihood']}/100")
    y -= 24 * mm

    c.setFillColor(CYAN)
    c.setFont("Helvetica", 8)
    c.drawString(12 * mm, y, "DECISION RATIONALE  (each weight is additive toward AI-likelihood)")
    y -= 6 * mm
    c.setFont("Helvetica", 8)
    for sig in analysis.get("signals", [])[:8]:
        c.setFillColor(SAFFRON if sig["weight"] > 0 else GREEN)
        c.drawString(12 * mm, y, f"{sig['weight']:+.1f}")
        c.setFillColor(PAPER)
        c.drawString(24 * mm, y, f"{sig['code']}")
        y -= 4 * mm
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 7)
        c.drawString(24 * mm, y, sig["rationale"][:110])
        c.setFont("Helvetica", 8)
        y -= 5 * mm

    gens = analysis.get("generators") or []
    y -= 2 * mm
    c.setFillColor(CYAN)
    c.drawString(12 * mm, y, "SOURCE TRACE")
    y -= 5 * mm
    c.setFillColor(PAPER)
    if gens:
        for g in gens:
            c.drawString(12 * mm, y, f"• {g['generator']}   matched {', '.join(g.get('matched') or [])}   conf {g.get('confidence', 0):.2f}")
            y -= 4.5 * mm
    else:
        c.setFillColor(MUTED)
        c.drawString(12 * mm, y, "No generator metadata hit. Frequency / ELA priors used. Reverse-search cluster in console.")
        y -= 5 * mm

    overlay = analysis.get("overlay_name")
    if overlay:
        p = settings.heatmap_dir / overlay
        if p.exists() and y > 70 * mm:
            c.setFillColor(CYAN)
            c.drawString(12 * mm, y, "MANIPULATION HEATMAP  (ELA + noise residual ensemble)")
            y -= 4 * mm
            c.drawImage(str(p), 12 * mm, max(38 * mm, y - 62 * mm), width=80 * mm, height=52 * mm, preserveAspectRatio=True, mask="auto")
            y = max(38 * mm, y - 64 * mm)

    c.showPage()
    c.setFillColor(NAVY)
    c.rect(0, 0, w, h, fill=1, stroke=0)
    c.setFillColor(PAPER)
    c.setFont("Times-Bold", 13)
    c.drawString(12 * mm, h - 18 * mm, "Chain of custody")
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawString(12 * mm, h - 24 * mm, "Hash-chained log. Each event seals the previous digest. Breaks are detectable.")
    y = h - 34 * mm
    c.setFont("Courier", 7)
    for ev in custody[:22]:
        c.setFillColor(CYAN)
        c.drawString(12 * mm, y, ev["timestamp"][:19].replace("T", " ") + "Z")
        c.setFillColor(PAPER)
        c.drawString(48 * mm, y, f"{ev['action']}  —  {ev['detail'][:70]}")
        y -= 3.6 * mm
        c.setFillColor(MUTED)
        c.drawString(48 * mm, y, ev["event_hash"][:32] + "…")
        y -= 5 * mm
        if y < 40 * mm:
            break

    c.setFillColor(STEEL)
    c.rect(12 * mm, 18 * mm, w - 24 * mm, 18 * mm, fill=1, stroke=0)
    payload = report_payload(case, evidence, analysis)
    sig = sign_payload(payload)
    content_hash = hashlib.sha256(payload.encode()).hexdigest()
    c.setFillColor(CYAN)
    c.setFont("Helvetica", 7)
    c.drawString(16 * mm, 30 * mm, "DIGITAL SIGNATURE  (HMAC-SHA256 station key — replace with HSM/DSC in production)")
    c.setFillColor(PAPER)
    c.setFont("Courier", 7)
    c.drawString(16 * mm, 24 * mm, f"SIG  {sig}")
    c.drawString(16 * mm, 20 * mm, f"HASH {content_hash}")

    c.setFillColor(MUTED)
    c.setFont("Helvetica", 6.5)
    c.drawString(
        12 * mm,
        10 * mm,
        "This report is an electronic record intended as FIR annexure. Prototype ensemble — validate against lab SOPs before charge-sheet.",
    )
    c.save()
    return {"signature": sig, "content_hash": content_hash}
