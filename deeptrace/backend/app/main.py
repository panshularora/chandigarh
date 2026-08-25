from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import router
from .config import settings
from .database import Base, engine
from .seed import enrich_demo, seed_if_empty
from .services.storage import ensure_dirs

ensure_dirs()
Base.metadata.create_all(bind=engine)
seed_if_empty()
if not settings.light_seed:
    enrich_demo()

app = FastAPI(title="DeepTrace", version="0.9.0", docs_url="/api/docs")
origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
allow_all = origins == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all else origins,
    allow_credentials=not allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

FRONTEND = Path(settings.frontend_dist) if settings.frontend_dist else Path(__file__).resolve().parents[2] / "frontend" / "dist"


@app.get("/api")
def api_root():
    return {"service": "DeepTrace", "team": "DigiSeva", "docs": "/api/docs"}


if FRONTEND.exists():
    assets = FRONTEND / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api"):
            return JSONResponse({"detail": "Not found"}, status_code=404)
        candidate = FRONTEND / path
        if candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND / "index.html"
        if index.exists():
            return FileResponse(index)
        return JSONResponse({"service": "DeepTrace", "docs": "/api/docs"})
else:

    @app.get("/")
    def root():
        return {"service": "DeepTrace", "team": "DigiSeva", "docs": "/api/docs", "hint": "frontend dist not built"}
