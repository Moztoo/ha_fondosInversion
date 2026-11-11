"""DataUpdateCoordinator for BBVA Fondos integration."""
import asyncio
from datetime import datetime, timedelta
import io
import logging
import re
from typing import Any, Dict, List, Optional
import httpx
import pypdf

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BBVA_DEFAULT_PDF_URL,
    CONF_API_URL,
    CONF_MODE,
    CONF_MODE_API,
    CONF_TRACKED_FUNDS,
    CONF_UPDATE_INTERVAL_HOURS,
    DEFAULT_API_URL,
    DEFAULT_MODE,
    DEFAULT_UPDATE_INTERVAL_HOURS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

class BBVAFondosCoordinator(DataUpdateCoordinator[Dict[str, Dict[str, Any]]]):
    """Central coordinator fetching BBVA funds performance data."""

    def __init__(self, hass: HomeAssistant, entry_data: Dict[str, Any]) -> None:
        self.entry_data = entry_data
        interval_hours = entry_data.get(
            CONF_UPDATE_INTERVAL_HOURS, DEFAULT_UPDATE_INTERVAL_HOURS
        )
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(hours=interval_hours),
        )
        self.mode = entry_data.get(CONF_MODE, DEFAULT_MODE)
        self.api_url = entry_data.get(CONF_API_URL, DEFAULT_API_URL).rstrip("/")
        self.tracked_funds: List[str] = entry_data.get(CONF_TRACKED_FUNDS, [])
        self.last_report_date: Optional[str] = None

    async def _async_update_data(self) -> Dict[str, Dict[str, Any]]:
        """Fetch data from either REST API or by downloading and parsing PDF directly."""
        try:
            if self.mode == CONF_MODE_API:
                return await self._fetch_from_api()
            else:
                return await self._fetch_and_parse_pdf()
        except Exception as err:
            raise UpdateFailed(f"Error fetching BBVA funds data: {err}") from err

    async def _fetch_from_api(self) -> Dict[str, Dict[str, Any]]:
        """Fetch tracked funds from the BBVA Fondos REST service."""
        result: Dict[str, Dict[str, Any]] = {}
        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            # First check health
            health_res = await client.get(f"{self.api_url}/api/v1/health", headers=headers)
            if health_res.status_code == 200:
                health_data = health_res.json().get("data", {})
                self.last_report_date = health_data.get("last_report_date")

            for item in self.tracked_funds:
                ticker, _, series = item.partition(":")
                ticker = ticker.strip().upper()
                series = series.strip().upper() if series else "B"

                url = f"{self.api_url}/api/v1/funds/{ticker}/{series}"
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json().get("data", {})
                    key = f"{ticker}:{series}"
                    snapshot = data.get("latest_snapshot") or {}
                    result[key] = {
                        "ticker": ticker,
                        "series": series,
                        "segment": data.get("segment", "Personas Físicas"),
                        "category": data.get("category", "Fondos de Inversión"),
                        "calificacion": data.get("calificacion"),
                        "minimo_inversion": data.get("minimo_inversion", 0.0),
                        "precio": snapshot.get("precio", 0.0),
                        "rendimiento_diario": snapshot.get("rendimiento_diario"),
                        "rendimiento_semanal": snapshot.get("rendimiento_semanal"),
                        "rendimiento_mes": snapshot.get("rendimiento_mes"),
                        "rendimiento_anio": snapshot.get("rendimiento_anio"),
                        "rendimiento_1a": snapshot.get("rendimiento_1a"),
                        "rendimiento_2a": snapshot.get("rendimiento_2a"),
                        "report_date": snapshot.get("report_date", self.last_report_date),
                    }
                else:
                    _LOGGER.warning("Could not fetch fund %s:%s from API (HTTP %d)", ticker, series, res.status_code)

        return result

    async def _fetch_and_parse_pdf(self) -> Dict[str, Dict[str, Any]]:
        """Download and parse BBVA PDF directly inside Home Assistant executor."""
        headers = {
            "User-Agent": "Mozilla/5.0 (HomeAssistant; Linux) AppleWebKit/537.36",
            "Accept": "application/pdf,*/*",
        }

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            res = await client.get(BBVA_DEFAULT_PDF_URL, headers=headers)
            if res.status_code != 200 or not res.content.startswith(b"%PDF"):
                raise ValueError(f"Invalid PDF response from BBVA: HTTP {res.status_code}")
            pdf_bytes = res.content

        # Execute PDF parsing in worker thread to avoid blocking event loop
        return await self.hass.async_add_executor_job(self._parse_pdf_sync, pdf_bytes)

    def _parse_pdf_sync(self, pdf_bytes: bytes) -> Dict[str, Dict[str, Any]]:
        """Synchronously parse PDF bytes and filter for tracked funds."""
        reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
        all_data: Dict[str, Dict[str, Any]] = {}

        detected_date: Optional[str] = None
        current_segment = "Personas Físicas"
        current_category = "Fondos de Inversión"

        for page in reader.pages:
            text = page.extract_text() or ""
            lines = text.split("\n")

            for line in lines:
                l_str = line.strip()
                if not l_str:
                    continue

                if not detected_date:
                    m = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", l_str)
                    if m:
                        try:
                            dt = datetime.strptime(m.group(1), "%d/%m/%Y")
                            detected_date = dt.strftime("%Y-%m-%d")
                        except ValueError:
                            detected_date = m.group(1)

                if "Personas Físicas" in l_str and "Anaquel" not in l_str:
                    current_segment = "Personas Físicas"
                elif "Personas Morales" in l_str and "Anaquel" not in l_str:
                    current_segment = "Personas Morales"
                elif "Colaboradores BBVA" in l_str and "Anaquel" not in l_str:
                    current_segment = "Colaboradores BBVA"

                if l_str.startswith("Fondos de") or l_str.startswith("Fondos Ciclos"):
                    current_category = l_str
                    continue

                parts = l_str.split()
                if len(parts) >= 9 and any("%" in p for p in parts[-7:-1]):
                    try:
                        precio = float(parts[-1].replace(",", "").replace("%", ""))
                        rend_2a = float(parts[-2].replace(",", "").replace("%", ""))
                        rend_1a = float(parts[-3].replace(",", "").replace("%", ""))
                        rend_anio = float(parts[-4].replace(",", "").replace("%", ""))
                        rend_mes = float(parts[-5].replace(",", "").replace("%", ""))
                        rend_sem = float(parts[-6].replace(",", "").replace("%", ""))
                        rend_dia = float(parts[-7].replace(",", "").replace("%", ""))

                        ticker = parts[0].strip().upper()
                        series = parts[1].strip().upper()
                        minimo = float(parts[2].replace(",", ""))

                        rating_tokens = parts[3:-7]
                        calificacion = " ".join(rating_tokens).strip() if rating_tokens else None

                        key = f"{ticker}:{series}"
                        all_data[key] = {
                            "ticker": ticker,
                            "series": series,
                            "segment": current_segment,
                            "category": current_category,
                            "minimo_inversion": minimo,
                            "calificacion": calificacion,
                            "precio": precio,
                            "rendimiento_diario": rend_dia,
                            "rendimiento_semanal": rend_sem,
                            "rendimiento_mes": rend_mes,
                            "rendimiento_anio": rend_anio,
                            "rendimiento_1a": rend_1a,
                            "rendimiento_2a": rend_2a,
                            "report_date": detected_date or datetime.now().strftime("%Y-%m-%d"),
                        }
                    except Exception:
                        continue

        self.last_report_date = detected_date
        # If tracked funds specified, filter to them; otherwise return all found
        if self.tracked_funds:
            filtered = {}
            for tf in self.tracked_funds:
                tf_norm = tf.upper().strip()
                if tf_norm in all_data:
                    filtered[tf_norm] = all_data[tf_norm]
            return filtered or all_data

        return all_data
