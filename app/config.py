"""Configuration settings for BBVA Fondos service."""
import os
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent.parent

@dataclass
class Settings:
    # Service
    APP_NAME: str = "BBVA Fondos de Inversión API & Dashboard"
    APP_VERSION: str = "1.0.0"
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

settings = Settings()
