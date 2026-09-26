"""End-to-end: open a case, upload an exhibit, analyse it, issue a signed report, verify the HMAC."""
import io

import numpy as np
from PIL import Image

from app.models import Analysis, Case, Evidence, Report
from app.serialize import analysis_out, case_out, evidence_out
from app.services.custody import verify_chain
from app.services.report_pdf import report_payload, sign_payload, verify_signature


def _jpeg() -> bytes:
    rng = np.random.default_rng(1)
    arr = rng.integers(0, 255, size=(96, 128, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, "RGB").save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _issue_report(client, auth):
    case = client.post("/api/cases", json={"title": "HMAC report test"}, headers=auth)
    assert case.status_code == 200, case.text
    case_id = case.json()["id"]
    up = client.post(
        f"/api/cases/{case_id}/evidence",
        files={"file": ("exhibit.jpg", _jpeg(), "image/jpeg")},
        headers=auth,
    )
    assert up.status_code == 200, up.text
    an = client.post(f"/api/evidence/{up.json()['id']}/analyze", headers=auth)
    assert an.status_code == 200, an.text
    rep = client.post(f"/api/analyses/{an.json()['id']}/report", headers=auth)
    assert rep.status_code == 200, rep.text
    return case_id, rep.json()


def test_report_signature_verifies_and_detects_modification(client, auth, db):
    case_id, rep = _issue_report(client, auth)

    report = db.get(Report, rep["id"])
    analysis = db.get(Analysis, report.analysis_id)
    evidence = db.get(Evidence, analysis.evidence_id)
    case = db.get(Case, case_id)
    payload = report_payload(case_out(case), evidence_out(evidence), analysis_out(analysis))

    # Valid report: stored signature matches an HMAC over the payload.
    assert report.signature == sign_payload(payload)
    assert verify_signature(payload, report.signature) is True

    # Modified report: changing the verdict, the exhibit hash or the signature fails verification.
    verdict = analysis.verdict
    other = "REAL" if verdict != "REAL" else "AI_GENERATED"
    assert verify_signature(payload.replace(f"|{verdict}|", f"|{other}|"), report.signature) is False
    assert verify_signature(payload.replace(evidence.sha256, "0" * 64), report.signature) is False
    flipped = ("0" if report.signature[0] != "0" else "1") + report.signature[1:]
    assert verify_signature(payload, flipped) is False

    # The PDF exists and the whole flow is on an intact custody chain.
    pdf = client.get(f"/api/reports/{rep['id']}/file", headers=auth)
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert verify_chain(db, case_id) == (True, None)


def test_report_download_requires_auth(client, auth):
    _, rep = _issue_report(client, auth)
    assert client.get(f"/api/reports/{rep['id']}/file").status_code in (401, 403)


def test_signature_depends_on_secret_key(monkeypatch):
    from app.config import settings

    payload = "DT-CHD-2026-00441|abc|REAL|12.0"
    sig = sign_payload(payload)
    monkeypatch.setattr(settings, "secret_key", "a-different-key")
    assert verify_signature(payload, sig) is False
