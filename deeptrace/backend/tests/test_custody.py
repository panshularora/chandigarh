from sqlalchemy import text

from app.models import Case, CustodyEvent, Operator
from app.services.custody import append_event, verify_chain


def _new_case(db) -> Case:
    op = db.query(Operator).filter_by(username="inspector").one()
    n = db.query(Case).count()
    case = Case(
        public_id=f"DT-TEST-{n + 1:05d}",
        title="custody test",
        offence_type="digital_arrest",
        station="Cyber Cell, Chandigarh",
        created_by=op.id,
    )
    db.add(case)
    db.flush()
    return case


def test_append_event_builds_sha256_chain(db):
    case = _new_case(db)
    op_id = case.created_by
    e1 = append_event(db, case_id=case.id, operator_id=op_id, action="CASE_OPENED", detail="opened")
    e2 = append_event(db, case_id=case.id, operator_id=op_id, action="NOTE", detail="second")
    e3 = append_event(db, case_id=case.id, operator_id=op_id, action="NOTE", detail="third")
    db.commit()

    assert e1.prev_hash == "GENESIS"
    assert e2.prev_hash == e1.event_hash
    assert e3.prev_hash == e2.event_hash
    for ev in (e1, e2, e3):
        assert len(ev.event_hash) == 64
        int(ev.event_hash, 16)  # hex SHA-256 digest
    assert len({e1.event_hash, e2.event_hash, e3.event_hash}) == 3

    # Re-read from the database (SQLite drops tzinfo) and recompute the whole chain.
    db.expire_all()
    assert verify_chain(db, case.id) == (True, None)


def test_tampering_with_a_stored_row_breaks_the_chain(db):
    case = _new_case(db)
    op_id = case.created_by
    append_event(db, case_id=case.id, operator_id=op_id, action="CASE_OPENED", detail="opened")
    middle = append_event(db, case_id=case.id, operator_id=op_id, action="EVIDENCE_INGESTED", detail="exhibit.jpg SHA-256 abc")
    append_event(db, case_id=case.id, operator_id=op_id, action="ANALYSIS_RUN", detail="verdict REAL")
    db.commit()
    assert verify_chain(db, case.id) == (True, None)

    # Edit a past row directly in the database, bypassing the application.
    db.execute(text("UPDATE custody_events SET detail = :d WHERE id = :i"), {"d": "exhibit_swapped.jpg", "i": middle.id})
    db.commit()
    db.expire_all()

    ok, bad_id = verify_chain(db, case.id)
    assert ok is False
    assert bad_id == middle.id


def test_rewriting_a_hash_is_detected_by_the_next_link(db):
    case = _new_case(db)
    op_id = case.created_by
    first = append_event(db, case_id=case.id, operator_id=op_id, action="CASE_OPENED", detail="opened")
    second = append_event(db, case_id=case.id, operator_id=op_id, action="NOTE", detail="n")
    db.commit()

    db.execute(text("UPDATE custody_events SET event_hash = :h WHERE id = :i"), {"h": "0" * 64, "i": first.id})
    db.commit()
    db.expire_all()

    ok, bad_id = verify_chain(db, case.id)
    assert ok is False
    assert bad_id in (first.id, second.id)


def test_seeded_demo_cases_have_intact_chains(db):
    # Only the seeded demo cases; other tests in this module deliberately tamper with their own cases.
    case_ids = [
        cid
        for (cid,) in db.query(CustodyEvent.case_id).join(Case, Case.id == CustodyEvent.case_id)
        .filter(Case.public_id.like("DT-CHD-%")).distinct()
    ]
    assert case_ids, "seed should create custody events"
    for cid in case_ids:
        assert verify_chain(db, cid)[0], f"case {cid} chain broken"
