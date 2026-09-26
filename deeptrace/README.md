# DeepTrace

Indigenous forensic console for **Chandigarh Police Cyber Cell** — Team **DigiSeva**.

Built from the pitch *AI-Generated Media Detection & Source Tracing* (PS4). Detect. Trace. Report.

## What this prototype does

- Ingests **image / video / audio** exhibits with SHA-256 and a hash-chained **chain of custody**
- Runs an **explainable ensemble** (ELA, noise residual, FFT lattice, EXIF/XMP generator fingerprints, temporal residual, spectral TTS cues)
- Paints a **manipulation heatmap** on a light-table viewer
- Traces **generator priors** (Midjourney, FaceFusion, Stable Diffusion, C2PA, …) and a local provenance graph
- Issues an **HMAC-signed PDF** written as a BSA 2023 s.63 FIR annexure
- Optional **SpaceXAI (grok-4.6)** investigator briefing when `XAI_API_KEY` is set
- **English / Hindi / Punjabi** station UI

This is a 24-hour hackathon-grade station tool: real forensic signals, not a random score. Production would swap the heuristic pack for ONNX EfficientNet-B4 / Xception / AASIST weights and a DSC/HSM for signatures — the case file, custody chain, and report shape stay the same.

## Stack

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | React 19 + Vite + TypeScript + GSAP | Fast console, no SaaS chrome |
| Backend | FastAPI | Matches the pitch; typed, async-ready |
| Database | SQLite (SQLAlchemy 2) | Zero-ops on a police laptop; Postgres URL drop-in |
| Forensics | Pillow + NumPy + OpenCV | Runs offline / air-gapped |
| Reports | ReportLab + HMAC-SHA256 | Court-shaped PDF today, DSC tomorrow |
| Briefing | xAI `grok-4.6` (optional) | SpaceXAI, server-side only |

## Run (Windows)

Two terminals from `deeptrace/`.

**Backend**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DEMO_MODE = "true"   # or set a real SECRET_KEY; the API refuses to start with the placeholder key otherwise
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```powershell
cd frontend
npm install
npm run dev
```

Or, from `deeptrace/`: `.\start.ps1`

Production (Docker): the API also serves the built console on port 8000.

Open [http://localhost:5173](http://localhost:5173)

```
inspector / chandigarh2026
sp.cyber  / chandigarh2026
analyst   / chandigarh2026
```

Seeded cases: digital-arrest still + call clip, synthetic blackmail image, voice-clone WAV, Sector 17 CCTV still.

Console routes after login: duty desk, case files, light table, signed annexure archive, custody audit, station brief.

## API

Swagger at [http://127.0.0.1:8000/api/docs](http://127.0.0.1:8000/api/docs)

## Scale path

1. Point `DATABASE_URL` at PostgreSQL
2. Put uploads on object storage; keep hashes in DB
3. Load ONNX detectors beside the current ensemble (same `Analysis` row)
4. Replace HMAC with a station DSC / HSM
5. Keep the console. The schema does not change.
