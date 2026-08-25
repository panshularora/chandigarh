from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from .config import settings
from .database import get_db
from .models import Analysis, Case, CustodyEvent, Evidence, Operator, Report
from .schemas import BriefingIn, CaseIn, LoginIn
from .security import current_operator, make_token, verify_password
from .serialize import analysis_out, case_out, custody_out, evidence_out, op_out, report_out
from .services.briefing import grok_briefing
from .services.custody import append_event
from .services.forensic import provenance_for, run_analysis
from .services.report_pdf import build_report
from .services.storage import hashes_of, media_kind, save_upload, upload_path

router = APIRouter()


def next_public_id(db: Session) -> str:
    n = db.query(Case).count() + 1
    return f"DT-CHD-2026-{440 + n:05d}"


@router.get("/health")
def health():
    return {"ok": True, "service": "deeptrace", "mode": "forensic-prototype"}


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    op = db.query(Operator).filter(Operator.username == body.username).first()
    if not op or not verify_password(body.password, op.password_hash):
        raise HTTPException(401, "Invalid operator credentials")
    return {"token": make_token(op), "operator": op_out(op)}


@router.get("/me")
def me(op: Operator = Depends(current_operator)):
    return op_out(op)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    cases = db.query(Case).options(
        joinedload(Case.evidence).joinedload(Evidence.analyses),
        joinedload(Case.creator),
    ).order_by(Case.created_at.desc()).all()
    analyses = db.query(Analysis).all()
    by_verdict = {"AI_GENERATED": 0, "REAL": 0, "INCONCLUSIVE": 0}
    for a in analyses:
        by_verdict[a.verdict] = by_verdict.get(a.verdict, 0) + 1
    open_p1 = sum(1 for c in cases if c.priority == "P1" and c.status != "closed")
    return {
        "operator": op_out(op),
        "kpis": {
            "open_cases": sum(1 for c in cases if c.status != "closed"),
            "exhibits": db.query(Evidence).count(),
            "ai_flagged": by_verdict.get("AI_GENERATED", 0),
            "reports": db.query(Report).count(),
            "p1_queue": open_p1,
        },
        "verdicts": by_verdict,
        "queue": [case_out(c) for c in cases[:12]],
    }


@router.get("/cases")
def list_cases(db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    rows = db.query(Case).options(
        joinedload(Case.creator),
        joinedload(Case.evidence).joinedload(Evidence.analyses),
    ).order_by(Case.created_at.desc()).all()
    return [case_out(c) for c in rows]


@router.post("/cases")
def create_case(body: CaseIn, db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    c = Case(
        public_id=next_public_id(db),
        fir_number=body.fir_number,
        title=body.title,
        offence_type=body.offence_type,
        station=body.station,
        priority=body.priority,
        summary=body.summary,
        status="open",
        created_by=op.id,
    )
    db.add(c)
    db.flush()
    append_event(db, case_id=c.id, operator_id=op.id, action="CASE_OPENED", detail=body.title)
    db.commit()
    db.refresh(c)
    return case_out(c)


@router.get("/cases/{case_id}")
def get_case(case_id: int, db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    c = db.query(Case).options(
        joinedload(Case.creator),
        joinedload(Case.evidence).joinedload(Evidence.analyses),
        joinedload(Case.reports),
    ).filter(Case.id == case_id).first()
    if not c:
        raise HTTPException(404, "Case not found")
    ops = {o.id: o for o in db.query(Operator).all()}
    custody = (
        db.query(CustodyEvent).filter(CustodyEvent.case_id == c.id).order_by(CustodyEvent.id.asc()).all()
    )
    analyses = db.query(Analysis).filter(Analysis.case_id == c.id).order_by(Analysis.id.desc()).all()
    return {
        "case": case_out(c),
        "evidence": [evidence_out(e) for e in c.evidence],
        "analyses": [analysis_out(a) for a in analyses],
        "custody": [custody_out(e, ops) for e in custody],
        "reports": [report_out(r) for r in c.reports],
    }


@router.post("/cases/{case_id}/evidence")
async def upload_evidence(
    case_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    op: Operator = Depends(current_operator),
):
    c = db.get(Case, case_id)
    if not c:
        raise HTTPException(404, "Case not found")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > 80 * 1024 * 1024:
        raise HTTPException(413, "Exhibit exceeds 80 MB prototype cap")
    sha256, sha1 = hashes_of(data)
    suffix = Path(file.filename or "exhibit.bin").suffix.lower() or ".bin"
    stored = save_upload(data, suffix)
    kind = media_kind(file.filename or stored, file.content_type or "")
    if kind == "unknown":
        raise HTTPException(400, "Supported exhibits: image, video, audio")
    ev = Evidence(
        case_id=c.id,
        filename=file.filename or stored,
        stored_name=stored,
        media_type=kind,
        mime=file.content_type or "application/octet-stream",
        sha256=sha256,
        sha1=sha1,
        size_bytes=len(data),
        uploaded_by=op.id,
    )
    db.add(ev)
    db.flush()
    c.status = "ingested"
    c.updated_at = datetime.now(timezone.utc)
    append_event(
        db,
        case_id=c.id,
        operator_id=op.id,
        action="EVIDENCE_INGESTED",
        detail=f"{ev.filename}  SHA-256 {sha256[:16]}…",
        evidence_id=ev.id,
    )
    db.commit()
    db.refresh(ev)
    return evidence_out(ev)


@router.post("/evidence/{evidence_id}/analyze")
def analyze(
    evidence_id: int,
    db: Session = Depends(get_db),
    op: Operator = Depends(current_operator),
):
    ev = db.query(Evidence).options(joinedload(Evidence.case)).filter(Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(404, "Exhibit not found")
    path = upload_path(ev.stored_name)
    if not path.exists():
        raise HTTPException(410, "Stored exhibit missing from station disk")
    result = run_analysis(path, ev.media_type)

    others = []
    for a in db.query(Analysis).all():
        try:
            meta = json.loads(a.metadata_json or "{}")
        except Exception:
            meta = {}
        case = db.get(Case, a.case_id)
        others.append({"id": a.id, "public_id": case.public_id if case else str(a.case_id), "metadata": meta})
    ahash = (result.get("metadata") or {}).get("ahash", "")
    result["provenance"] = provenance_for(ahash, result.get("generators") or [], others)

    row = Analysis(
        case_id=ev.case_id,
        evidence_id=ev.id,
        operator_id=op.id,
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
    db.add(row)
    case = db.get(Case, ev.case_id)
    if case:
        case.status = "analyzed"
        case.updated_at = datetime.now(timezone.utc)
    append_event(
        db,
        case_id=ev.case_id,
        operator_id=op.id,
        action="ANALYSIS_COMPLETE",
        detail=f"{result['verdict']}  conf {result['confidence']}%  AI {result['ai_likelihood']}",
        evidence_id=ev.id,
    )
    db.commit()
    db.refresh(row)
    return analysis_out(row)


@router.post("/analyses/{analysis_id}/briefing")
def briefing(
    analysis_id: int,
    body: BriefingIn | None = None,
    db: Session = Depends(get_db),
    op: Operator = Depends(current_operator),
):
    a = db.get(Analysis, analysis_id)
    if not a:
        raise HTTPException(404, "Analysis not found")
    ev = db.get(Evidence, a.evidence_id)
    case = db.get(Case, a.case_id)
    packed_case, packed_a, packed_ev = case_out(case), analysis_out(a), evidence_out(ev)
    if body is not None and body.use_grok is False:
        from .services.briefing import local_briefing

        text = local_briefing(packed_case, packed_a, packed_ev)
    else:
        text = grok_briefing(packed_case, packed_a, packed_ev)
    a.briefing = text
    append_event(db, case_id=a.case_id, operator_id=op.id, action="BRIEFING_ISSUED", detail="Investigator note generated", evidence_id=a.evidence_id)
    db.commit()
    return {"briefing": text}


@router.post("/analyses/{analysis_id}/report")
def make_report(
    analysis_id: int,
    db: Session = Depends(get_db),
    op: Operator = Depends(current_operator),
):
    a = db.get(Analysis, analysis_id)
    if not a:
        raise HTTPException(404, "Analysis not found")
    ev = db.get(Evidence, a.evidence_id)
    case = db.get(Case, a.case_id)
    ops = {o.id: o for o in db.query(Operator).all()}
    custody = db.query(CustodyEvent).filter(CustodyEvent.case_id == a.case_id).order_by(CustodyEvent.id.asc()).all()
    fname = f"{case.public_id}_{analysis_id}.pdf"
    dest = settings.report_dir / fname
    packed = analysis_out(a)
    sealed = build_report(
        dest=dest,
        case=case_out(case),
        evidence=evidence_out(ev),
        analysis=packed,
        custody=[custody_out(e, ops) for e in custody],
        operator=op_out(op),
    )
    rep = Report(
        case_id=case.id,
        analysis_id=a.id,
        filename=fname,
        content_hash=sealed["content_hash"],
        signature=sealed["signature"],
        generated_by=op.id,
    )
    db.add(rep)
    case.status = "reported"
    append_event(db, case_id=case.id, operator_id=op.id, action="REPORT_SIGNED", detail=f"HMAC {sealed['signature'][:16]}…", evidence_id=ev.id)
    db.commit()
    db.refresh(rep)
    return report_out(rep)


@router.get("/reports/{report_id}/file")
def download_report(report_id: int, db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    r = db.get(Report, report_id)
    if not r:
        raise HTTPException(404, "Report not found")
    path = settings.report_dir / r.filename
    if not path.exists():
        raise HTTPException(410, "PDF missing")
    return FileResponse(path, media_type="application/pdf", filename=r.filename)


@router.get("/media/{kind}/{name}")
def media(kind: str, name: str, op: Operator = Depends(current_operator)):
    if ".." in name or "/" in name or "\\" in name:
        raise HTTPException(400, "Bad path")
    folder = {"uploads": settings.upload_dir, "heatmaps": settings.heatmap_dir, "reports": settings.report_dir}.get(kind)
    if not folder:
        raise HTTPException(404, "Unknown store")
    path = folder / name
    if not path.exists():
        raise HTTPException(404, "Not found")
    mime = "application/octet-stream"
    if name.endswith(".png"):
        mime = "image/png"
    elif name.endswith((".jpg", ".jpeg")):
        mime = "image/jpeg"
    elif name.endswith(".webp"):
        mime = "image/webp"
    elif name.endswith(".pdf"):
        mime = "application/pdf"
    elif name.endswith(".wav"):
        mime = "audio/wav"
    elif name.endswith(".mp4"):
        mime = "video/mp4"
    return FileResponse(path, media_type=mime)


@router.get("/reports")
def list_reports(db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    rows = db.query(Report).order_by(Report.id.desc()).all()
    cases = {c.id: c for c in db.query(Case).all()}
    analyses = {a.id: a for a in db.query(Analysis).all()}
    out = []
    for r in rows:
        d = report_out(r)
        c = cases.get(r.case_id)
        a = analyses.get(r.analysis_id)
        d["public_id"] = c.public_id if c else ""
        d["title"] = c.title if c else ""
        d["verdict"] = a.verdict if a else None
        d["confidence"] = a.confidence if a else None
        out.append(d)
    return out


@router.get("/audit")
def audit_log(db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    ops = {o.id: o for o in db.query(Operator).all()}
    cases = {c.id: c.public_id for c in db.query(Case).all()}
    rows = db.query(CustodyEvent).order_by(CustodyEvent.id.desc()).limit(120).all()
    out = []
    for e in rows:
        d = custody_out(e, ops)
        d["public_id"] = cases.get(e.case_id, "")
        d["case_id"] = e.case_id
        out.append(d)
    return out


@router.get("/operators")
def operators(db: Session = Depends(get_db), op: Operator = Depends(current_operator)):
    return [op_out(o) for o in db.query(Operator).all()]
