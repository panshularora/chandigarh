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

## Deploy on Vercel

```powershell
cd C:\Users\Panshul\Desktop\chandigarh
vercel --yes --prod
```

Static console + FastAPI at `/api`. Demo: `inspector` / `chandigarh2026`.

## Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/panshularora/chandigarh)

One click on that button applies `render.yaml` (Docker web service, `/api/health` check).

Image (after CI): `ghcr.io/panshularora/chandigarh:latest`

## Stack

React 19 + Vite · FastAPI · SQLite · Pillow/NumPy/OpenCV forensics · ReportLab HMAC PDFs · optional SpaceXAI (`XAI_API_KEY`) briefings · EN/HI/PA
