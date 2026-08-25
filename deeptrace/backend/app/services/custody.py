import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import CustodyEvent


def append_event(
    db: Session,
    *,
    case_id: int,
    operator_id: int,
    action: str,
    detail: str = "",
    evidence_id: int | None = None,
) -> CustodyEvent:
    last = (
        db.query(CustodyEvent)
        .filter(CustodyEvent.case_id == case_id)
        .order_by(CustodyEvent.id.desc())
        .first()
    )
    prev = last.event_hash if last else "GENESIS"
    ts = datetime.now(timezone.utc)
    raw = f"{prev}|{ts.isoformat()}|{case_id}|{evidence_id}|{operator_id}|{action}|{detail}"
    event_hash = hashlib.sha256(raw.encode()).hexdigest()
    ev = CustodyEvent(
        case_id=case_id,
        evidence_id=evidence_id,
        operator_id=operator_id,
        action=action,
        detail=detail,
        timestamp=ts,
        prev_hash=prev,
        event_hash=event_hash,
    )
    db.add(ev)
    db.flush()
    return ev
