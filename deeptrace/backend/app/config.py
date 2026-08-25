from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT.parent / ".env"), extra="ignore")

    app_name: str = "DeepTrace"
    secret_key: str = "deeptrace-chandigarh-cyber-cell-prototype-key-change-in-prod"
    jwt_alg: str = "HS256"
    jwt_hours: int = 12
    database_url: str = f"sqlite:///{(ROOT / 'data' / 'deeptrace.db').as_posix()}"
    data_dir: Path = ROOT / "data"
    upload_dir: Path = ROOT / "data" / "uploads"
    heatmap_dir: Path = ROOT / "data" / "heatmaps"
    report_dir: Path = ROOT / "data" / "reports"
    xai_api_key: str = ""
    xai_model: str = "grok-4.6"
    xai_base_url: str = "https://api.x.ai/v1"
    cors_origins: str = "*"
    frontend_dist: str = ""
    light_seed: bool = False


settings = Settings()
if not settings.xai_api_key:
    import os

    settings.xai_api_key = os.environ.get("XAI_API_KEY", "")
