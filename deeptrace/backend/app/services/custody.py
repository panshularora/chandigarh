import hashlib
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import CustodyEvent


def _event_digest(prev: str, ts: datetime, case_id: int, evidence_id: int | None, operator_id: int, action: str, detail: str) -> str:
    raw = f"{prev}|{ts.isoformat()}|{case_id}|{evidence_id}|{operator_id}|{action}|{detail}"
    return hashlib.sha256(raw.encode()).hexdigest()


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
    event_hash = _event_digest(prev, ts, case_id, evidence_id, operator_id, action, detail)
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


def verify_chain(db: Session, case_id: int) -> tuple[bool, int | None]:
    """Recompute a case's custody chain.

    Returns ``(True, None)`` if every event links to its predecessor and its stored
    hash matches its contents, else ``(False, id_of_first_bad_event)``.
    """
    events = (
        db.query(CustodyEvent)
        .filter(CustodyEvent.case_id == case_id)
        .order_by(CustodyEvent.id.asc())
        .all()
    )
    prev = "GENESIS"
    for ev in events:
        ts = ev.timestamp
        if ts.tzinfo is None:  # SQLite drops tzinfo; events are always written in UTC
            ts = ts.replace(tzinfo=timezone.utc)
        expected = _event_digest(prev, ts, ev.case_id, ev.evidence_id, ev.operator_id, ev.action, ev.detail)
        if ev.prev_hash != prev or ev.event_hash != expected:
            return False, ev.id
        prev = ev.event_hash
    return True, None
