"""Scraper module for downloading BBVA Anaquel de Rendimientos PDF."""
import logging
from pathlib import Path
from typing import Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger("bbva_fondos.scraper")

class ScraperError(Exception):
    """Custom exception raised when PDF download fails."""
    pass

class BBVAScraper:
    """Manages downloading and caching of the BBVA Fondos Anaquel PDF."""

    def __init__(
        self,
        primary_url: Optional[str] = None,
        backup_url: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.primary_url = primary_url or settings.BBVA_PDF_URL
        self.backup_url = backup_url or settings.BBVA_BACKUP_PDF_URL
        self.timeout = timeout or settings.PDF_DOWNLOAD_TIMEOUT_SECONDS
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/pdf,*/*",
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        }

    async def fetch_pdf_bytes_async(self) -> Tuple[bytes, str]:
        """Download the latest Anaquel PDF asynchronously.

        Returns:
            Tuple of (pdf_bytes, source_url)
        """
        urls_to_try = [self.primary_url, self.backup_url]
        last_error = None

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for url in urls_to_try:
                try:
                    logger.info("Attempting to fetch PDF from: %s", url)
                    response = await client.get(url, headers=self.headers)
                    if response.status_code == 200 and len(response.content) > 1000:
                        # Verify PDF header magic bytes '%PDF'
                        if response.content.startswith(b"%PDF"):
                            logger.info("Successfully fetched %d bytes from %s", len(response.content), url)
                            return response.content, url
                        else:
                            logger.warning("Response from %s did not begin with %%PDF header", url)
                    else:
                        logger.warning("Fetch failed from %s: HTTP %d", url, response.status_code)
                except Exception as e:
                    logger.warning("Error downloading from %s: %s", url, e)
                    last_error = e

        raise ScraperError(f"Could not download Anaquel PDF from any known source. Last error: {last_error}")

    def fetch_pdf_bytes_sync(self) -> Tuple[bytes, str]:
        """Download the latest Anaquel PDF synchronously."""
        urls_to_try = [self.primary_url, self.backup_url]
        last_error = None

        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            for url in urls_to_try:
                try:
                    logger.info("Sync fetch attempt from: %s", url)
                    response = client.get(url, headers=self.headers)
                    if response.status_code == 200 and len(response.content) > 1000:
                        if response.content.startswith(b"%PDF"):
                            logger.info("Successfully fetched %d bytes from %s", len(response.content), url)
                            return response.content, url
                except Exception as e:
                    last_error = e

        raise ScraperError(f"Could not download Anaquel PDF synchronously: {last_error}")
