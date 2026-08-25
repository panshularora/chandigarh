from __future__ import annotations

import json

from ..config import settings

SYSTEM = (
    "You are DeepTrace, an indigenous forensic briefing officer for Chandigarh Police Cyber Cell. "
    "Write a tight investigator note (not marketing). Use short paragraphs. "
    "State verdict, the 3 strongest signals, likely generator if any, "
    "and the next investigative step under Indian criminal procedure "
    "(BSA 2023 electronic records, FIR annexure). Do not invent facts beyond the JSON."
)


def local_briefing(case: dict, analysis: dict, evidence: dict) -> str:
    gens = ", ".join(g["generator"] for g in (analysis.get("generators") or [])) or "no metadata generator hit"
    top = analysis.get("signals") or []
    top = sorted(top, key=lambda s: abs(s.get("weight", 0)), reverse=True)[:3]
    lines = " ".join(f"{s['code']} ({s['weight']:+.1f}): {s['rationale']}" for s in top)
    return (
        f"Exhibit {evidence.get('filename')} in {case.get('public_id')} is assessed "
        f"{analysis.get('verdict', '').replace('_', ' ')} "
        f"at {analysis.get('confidence')}% confidence (AI-likelihood {analysis.get('ai_likelihood')}/100). "
        f"Source prior: {gens}. "
        f"Primary signals — {lines} "
        f"Recommended next step: annex the signed PDF to the FIR/GD, preserve the original bit-for-bit "
        f"(SHA-256 {evidence.get('sha256', '')[:16]}…), and request the originating platform logs if a generator is named."
    )


def grok_briefing(case: dict, analysis: dict, evidence: dict) -> str:
    if not settings.xai_api_key:
        return local_briefing(case, analysis, evidence)
    payload = {
        "case": {k: case.get(k) for k in ("public_id", "title", "offence_type", "fir_number", "station")},
        "evidence": {k: evidence.get(k) for k in ("filename", "media_type", "sha256")},
        "analysis": {
            "verdict": analysis.get("verdict"),
            "confidence": analysis.get("confidence"),
            "ai_likelihood": analysis.get("ai_likelihood"),
            "signals": analysis.get("signals"),
            "generators": analysis.get("generators"),
            "metadata": analysis.get("metadata"),
        },
    }
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.xai_api_key, base_url=settings.xai_base_url)
        try:
            resp = client.responses.create(
                model=settings.xai_model,
                input=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            text = getattr(resp, "output_text", None)
            if text:
                return text.strip()
        except Exception:
            chat = client.chat.completions.create(
                model=settings.xai_model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
            )
            return (chat.choices[0].message.content or "").strip()
    except Exception as exc:
        note = local_briefing(case, analysis, evidence)
        return note + f" (SpaceXAI briefing unavailable: {exc.__class__.__name__})"
    return local_briefing(case, analysis, evidence)
