from .models import Analysis, Case, CustodyEvent, Evidence, Operator, Report


def op_out(o: Operator) -> dict:
    return {
        "id": o.id,
        "username": o.username,
        "full_name": o.full_name,
        "role": o.role,
        "station": o.station,
        "badge_no": o.badge_no,
        "language": o.language,
    }


def case_out(c: Case, *, evidence_count: int | None = None, latest: Analysis | None = None) -> dict:
    if latest is None:
        found: list[Analysis] = []
        for e in c.evidence or []:
            found.extend(e.analyses or [])
        if found:
            flagged = [a for a in found if a.verdict == "AI_GENERATED"]
            latest = max(flagged, key=lambda a: a.ai_likelihood) if flagged else max(found, key=lambda a: a.id)
    return {
        "id": c.id,
        "public_id": c.public_id,
        "fir_number": c.fir_number,
        "title": c.title,
        "offence_type": c.offence_type,
        "station": c.station,
        "status": c.status,
        "priority": c.priority,
        "summary": c.summary,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
        "creator": op_out(c.creator) if c.creator else None,
        "evidence_count": evidence_count if evidence_count is not None else len(c.evidence or []),
        "latest_verdict": latest.verdict if latest else None,
        "latest_confidence": latest.confidence if latest else None,
        "latest_ai": latest.ai_likelihood if latest else None,
    }


def evidence_out(e: Evidence) -> dict:
    latest = e.analyses[-1] if e.analyses else None
    return {
        "id": e.id,
        "case_id": e.case_id,
        "filename": e.filename,
        "stored_name": e.stored_name,
        "media_type": e.media_type,
        "mime": e.mime,
        "sha256": e.sha256,
        "sha1": e.sha1,
        "size_bytes": e.size_bytes,
        "uploaded_at": e.uploaded_at.isoformat() if e.uploaded_at else None,
        "latest_analysis_id": latest.id if latest else None,
        "latest_verdict": latest.verdict if latest else None,
    }


def analysis_out(a: Analysis) -> dict:
    import json

    def loads(s: str):
        try:
            return json.loads(s) if s else []
        except Exception:
            return s

    return {
        "id": a.id,
        "case_id": a.case_id,
        "evidence_id": a.evidence_id,
        "status": a.status,
        "verdict": a.verdict,
        "confidence": a.confidence,
        "ai_likelihood": a.ai_likelihood,
        "signals": loads(a.signals_json),
        "generators": loads(a.generators_json),
        "provenance": loads(a.provenance_json),
        "metadata": loads(a.metadata_json),
        "heatmap_name": a.heatmap_name,
        "overlay_name": a.overlay_name,
        "briefing": a.briefing,
        "model_versions": loads(a.model_versions),
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def custody_out(e: CustodyEvent, operators: dict[int, Operator]) -> dict:
    op = operators.get(e.operator_id)
    return {
        "id": e.id,
        "action": e.action,
        "detail": e.detail,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "prev_hash": e.prev_hash,
        "event_hash": e.event_hash,
        "operator": op.full_name if op else str(e.operator_id),
        "badge": op.badge_no if op else "",
        "evidence_id": e.evidence_id,
    }


def report_out(r: Report) -> dict:
    return {
        "id": r.id,
        "case_id": r.case_id,
        "analysis_id": r.analysis_id,
        "filename": r.filename,
        "content_hash": r.content_hash,
        "signature": r.signature,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    }
