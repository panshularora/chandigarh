import logging
import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[1]
ON_VERCEL = bool(os.environ.get("VERCEL"))
DATA_ROOT = Path("/tmp/deeptrace") if ON_VERCEL else (ROOT / "data")
DEFAULT_SECRET_KEY = "deeptrace-chandigarh-cyber-cell-prototype-key-change-in-prod"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT.parent / ".env"), extra="ignore")

    app_name: str = "DeepTrace"
    secret_key: str = DEFAULT_SECRET_KEY
    jwt_alg: str = "HS256"
    jwt_hours: int = 12
    database_url: str = f"sqlite:///{(DATA_ROOT / 'deeptrace.db').as_posix()}"
    data_dir: Path = DATA_ROOT
    upload_dir: Path = DATA_ROOT / "uploads"
    heatmap_dir: Path = DATA_ROOT / "heatmaps"
    report_dir: Path = DATA_ROOT / "reports"
    xai_api_key: str = ""
    xai_model: str = "grok-4.6"
    xai_base_url: str = "https://api.x.ai/v1"
    cors_origins: str = "*"
    frontend_dist: str = ""
    light_seed: bool = ON_VERCEL
    # DEMO_MODE=true allows the placeholder SECRET_KEY (throwaway demo deployments only).
    # The Vercel preview is an ephemeral demo (SQLite in /tmp), so it defaults to demo mode.
    demo_mode: bool = ON_VERCEL


def check_secret_key(cfg: Settings) -> None:
    """Refuse to start with the placeholder SECRET_KEY unless DEMO_MODE is on.

    SECRET_KEY signs the JWT sessions and the report HMACs, so a publicly known
    key would let anyone forge a login or a report signature.
    """
    if cfg.secret_key and cfg.secret_key != DEFAULT_SECRET_KEY:
        return
    if cfg.demo_mode:
        logging.getLogger("deeptrace").warning(
            "DEMO_MODE is on and SECRET_KEY is the built-in placeholder; "
            "sessions and report signatures are forgeable. Do not use this outside a demo."
        )
        if not cfg.secret_key:
            cfg.secret_key = DEFAULT_SECRET_KEY
        return
    raise RuntimeError(
        "SECRET_KEY is unset or equal to the built-in placeholder. "
        "Set SECRET_KEY to a long random value (e.g. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`), "
        "or set DEMO_MODE=true for a throwaway demo."
    )


settings = Settings()
if not settings.xai_api_key:
    settings.xai_api_key = os.environ.get("XAI_API_KEY", "")
