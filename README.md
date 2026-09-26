# DeepTrace: forensic console for suspected AI-generated media

A login-gated web console for a police cyber cell (built for the Chandigarh Police Cyber Cell problem statement, team DigiSeva). Investigators open a case and upload image, audio or video evidence. The console then:
- runs **signal-level forensic heuristics** on the evidence,
- records every action in a **tamper-evident chain of custody**,
- issues an **HMAC-signed PDF report**.

The UI is available in English, Hindi and Punjabi.

**Status:** a hackathon prototype (all commits on 25 Aug 2026). The detectors are **hand-built heuristics, not trained models**. There are no automated tests yet.

## What it does
| Area | Implementation | Where |
|---|---|---|
| Image analysis | Error-level analysis, noise residual, FFT spectral features, EXIF/PNG/XMP metadata parsing, generator-name priors (e.g., Midjourney, Stable Diffusion, C2PA tags), average-hash similarity for provenance, heatmap overlay | `backend/app/services/forensic.py`, `heatmap.py` |
| Audio / video | Spectral envelope and zero-crossing cues; temporal residual with per-frame voting | `services/forensic.py` |
| Chain of custody | Each event stores `SHA-256(prev_hash, timestamp, case, evidence, operator, action, detail)`, so editing any past row breaks the chain | `services/custody.py` |
| Reports | ReportLab PDF signed with HMAC-SHA256 over the report payload | `services/report_pdf.py` |
| Auth | JWT (HS256, 12 h) bearer tokens; passwords hashed with PBKDF2-HMAC-SHA256 (180k iterations, random salt, constant-time compare) | `backend/app/security.py` |
| Data | SQLAlchemy 2 on SQLite; cases, evidence, analyses, reports, audit log | `models.py`, `database.py` |
| Optional briefing | If `XAI_API_KEY` is set, generates an investigator summary via the xAI API; otherwise writes a local note | `services/briefing.py` |
| Frontend | React 19 + Vite + TypeScript, react-router, GSAP | `deeptrace/frontend/` |

## Run
**Docker (UI + API on one port):**
```bash
docker build -t deeptrace .
docker run --rm -p 8000:8000 -e SECRET_KEY=change-me deeptrace
# open http://localhost:8000  (demo login: inspector / chandigarh2026)
```
**Local dev:**
```bash
cd deeptrace/backend && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000
cd deeptrace/frontend && npm install && npm run dev      # http://localhost:5173
```
(`deeptrace/start.ps1` does both on Windows.) API docs are at `/api/docs`.

**Deploy options in the repo:** `render.yaml` (Docker web service with an `/api/health` check), `vercel.json` (static UI + Python function), and `.github/workflows/ci.yml`, which builds the image on every PR and pushes `ghcr.io/panshularora/chandigarh:latest` on pushes to `main`.

## Security notes (prototype)
- **Set `SECRET_KEY`.** The default in `config.py` is a placeholder, and it signs both the JWTs and the report HMACs.
- HMAC with a server key proves the report came from this server, not who signed it. A real deployment would use a digital-signature certificate or an HSM, as the code comments say.
- The demo operator account is seeded for evaluation. Disable it outside demos.

## Limitations
Heuristic scores can be fooled and have not been benchmarked on any labelled dataset. Treat the verdicts as investigative leads, not evidence.

## Next steps
Unit tests for the custody hash chain, HMAC verification and auth; a CI test job; a benchmark of the image heuristics on a public real-vs-generated dataset.

## Stack
Python, FastAPI, SQLAlchemy, Pydantic v2, PyJWT, Pillow, NumPy, OpenCV, ReportLab · React 19, TypeScript, Vite · Docker, GitHub Actions (GHCR), Render/Vercel configs.

The pitch deck is `DeepTrace_DigiSeva_Final (3).pptx`.
