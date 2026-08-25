# DeepTrace — DigiSeva

Indigenous forensic console for **Chandigarh Police Cyber Cell**. Detect AI-generated media, trace the generator, issue a court-shaped PDF.

Pitch deck: `DeepTrace_DigiSeva_Final (3).pptx`  
App: `deeptrace/`

**Demo login:** `inspector` / `chandigarh2026`

## Live / local

```powershell
cd deeptrace
.\start.ps1
```

Console: http://localhost:5173  
API docs: http://127.0.0.1:8000/api/docs

## Docker (frontend + API, one port)

```powershell
docker build -t deeptrace .
docker run --rm -p 8000:8000 deeptrace
```

Open http://localhost:8000

## Deploy on Render

This repo includes `render.yaml`. After the code is on GitHub:

1. Open [Render Blueprint](https://render.com/deploy?repo=https://github.com/panshularora/chandigarh)
2. Apply the `deeptrace` web service

Or: Render → New → Blueprint → pick `panshularora/chandigarh`.

## Stack

React 19 + Vite · FastAPI · SQLite · Pillow/NumPy/OpenCV forensics · ReportLab HMAC PDFs · optional SpaceXAI (`XAI_API_KEY`) briefings · EN/HI/PA
