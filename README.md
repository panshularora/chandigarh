# DeepTrace: forensic console for suspected AI-generated media

A login-gated web console for a police cyber cell (built for the Chandigarh Police Cyber Cell problem statement, team DigiSeva). Investigators open a case and upload image, audio or video evidence. The console then:
- runs **signal-level forensic heuristics** on the evidence,
- records every action in a **tamper-evident chain of custody**,
- issues an **HMAC-signed PDF report**.

The UI is available in English, Hindi and Punjabi.

**Status:** a hackathon prototype (all commits on 25 Aug 2026). The detectors are **hand-built heuristics, not trained models**. A pytest suite covers the custody chain, report HMACs, password hashing, JWT expiry, auth-protected routes and the `SECRET_KEY` startup guard; the forensic heuristics themselves are not unit-tested.

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
cd deeptrace/backend && pip install -r requirements.txt && DEMO_MODE=true uvicorn app.main:app --reload --port 8000
cd deeptrace/frontend && npm install && npm run dev      # http://localhost:5173
```
(`deeptrace/start.ps1` does both on Windows and sets `DEMO_MODE=true` if neither `SECRET_KEY` nor `DEMO_MODE` is set.) API docs are at `/api/docs`.

**Configuration:** the API refuses to start if `SECRET_KEY` is empty or the placeholder in `config.py`, unless `DEMO_MODE=true`. Use `DEMO_MODE=true` only for local or throwaway demos. Settings can also go in `deeptrace/.env` (see `deeptrace/.env.example`).

**Tests:**
```bash
cd deeptrace/backend && pip install -r requirements-dev.txt && python -m pytest
```
The tests use a temporary SQLite database and data directory (`tests/conftest.py`) and need no network.

**Deploy options in the repo:** `render.yaml` (Docker web service with an `/api/health` check), `vercel.json` (static UI + Python function), and `.github/workflows/ci.yml`. CI runs the pytest suite first. If it passes, CI builds the image on every PR and pushes `ghcr.io/panshularora/chandigarh:latest` on pushes to `main`. Render generates a random `SECRET_KEY`. The Vercel deployment currently uses the placeholder key, so it runs in demo mode (`demo_mode` defaults to true when `VERCEL` is set).

## Security notes (prototype)
- **Set `SECRET_KEY`.** It signs both the JWTs and the report HMACs. The default in `config.py` is a public placeholder, so the app fails at startup if it is used without `DEMO_MODE=true`. In demo mode, anyone who knows the placeholder can forge sessions and report signatures.
- HMAC with a server key proves the report came from this server, not who signed it. A real deployment would use a digital-signature certificate or an HSM, as the code comments say.
- The demo operator account is seeded for evaluation. Disable it outside demos.

## Limitations
Heuristic scores can be fooled and have not been benchmarked on any labelled dataset. Treat the verdicts as investigative leads, not evidence.

## Next steps
A benchmark of the image heuristics on a public real-vs-generated dataset.

## Stack
Python, FastAPI, SQLAlchemy, Pydantic v2, PyJWT, Pillow, NumPy, OpenCV, ReportLab · React 19, TypeScript, Vite · Docker, GitHub Actions (GHCR), Render/Vercel configs.

The pitch deck is `DeepTrace_DigiSeva_Final (3).pptx`.
