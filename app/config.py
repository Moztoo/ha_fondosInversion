"""Configuration settings for BBVA Fondos service."""
import json
import os
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent

# Read Home Assistant Add-on options if running inside Home Assistant
HA_OPTIONS = {}
HA_OPTIONS_PATH = Path("/data/options.json")
if HA_OPTIONS_PATH.exists():
    try:
        with open(HA_OPTIONS_PATH, "r", encoding="utf-8") as f:
            HA_OPTIONS = json.load(f)
    except Exception:
        pass

@dataclass
class Settings:
    # Service
    APP_NAME: str = "BBVA Fondos de Inversión API & Dashboard"
    APP_VERSION: str = "1.0.5"
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8088"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Database
    DATABASE_PATH: str = os.getenv(
        "DATABASE_PATH", str(BASE_DIR / "data" / "bbva_fondos.db")
    )

    # Scraper & Remote PDF
    BBVA_PDF_URL: str = os.getenv(
        "BBVA_PDF_URL",
        "https://portal.bbva.mx/siabinternet/Repositorio/import/doctos/analisis/00003776.pdf",
    )
    BBVA_BACKUP_PDF_URL: str = os.getenv(
        "BBVA_BACKUP_PDF_URL",
        "https://www.bbva.mx/content/dam/public-web/mexico/documents/empresas/fondos/home-fondos-de-inversion/do_6_Rendimientos_00003776.pdf",
    )
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    PDF_DOWNLOAD_TIMEOUT_SECONDS: int = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "30"))

    # Automated Scheduling
    AUTO_SYNC_ENABLED: bool = HA_OPTIONS.get(
        "auto_sync_enabled",
        os.getenv("AUTO_SYNC_ENABLED", "true").lower() in ("true", "1", "yes"),
    )
    AUTO_SYNC_TIME: str = HA_OPTIONS.get(
        "auto_sync_time",
        os.getenv("AUTO_SYNC_TIME", "22:00"),  # Default: 10:00 PM (22:00)
    )
    AUTO_SYNC_ON_STARTUP: bool = HA_OPTIONS.get(
        "auto_sync_on_startup",
        os.getenv("AUTO_SYNC_ON_STARTUP", "true").lower() in ("true", "1", "yes"),
    )

    # Home Assistant Notifications & Signals
    NOTIFY_DEVICE: str = HA_OPTIONS.get(
        "notify_device",
        os.getenv("NOTIFY_DEVICE", "mobile_app_sevastopol"),
    )
    SUPERVISOR_TOKEN: str = os.getenv("SUPERVISOR_TOKEN", "")
    HA_URL: str = os.getenv(
        "HA_URL",
        "http://supervisor/core/api" if os.getenv("SUPERVISOR_TOKEN") else "http://192.168.1.20:8123/api",
    )
    HA_TOKEN: str = os.getenv(
        "HA_TOKEN",
        os.getenv("SUPERVISOR_TOKEN", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmZmZjOTg4MTM1MTI0NmQ2YWI0NGJjZTIwMmVjNTJlNyIsImlhdCI6MTc4OTk1ODM1NSwiZXhwIjoyMTA1MzE4MzU1fQ.gNOGNPkFgzuhFKZOyNoI8hIp3TJWo773Yq_6Mmau3Mw"),
    )

settings = Settings()
