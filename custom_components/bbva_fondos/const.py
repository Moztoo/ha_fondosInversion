"""Constants for BBVA Fondos de Inversión Home Assistant integration."""

DOMAIN = "bbva_fondos"

CONF_MODE = "mode"
CONF_MODE_DIRECT = "direct_pdf"
CONF_MODE_API = "rest_api"

CONF_API_URL = "api_url"
CONF_TRACKED_FUNDS = "tracked_funds"
CONF_UPDATE_INTERVAL_HOURS = "update_interval_hours"

DEFAULT_MODE = CONF_MODE_DIRECT
DEFAULT_API_URL = "http://localhost:8088"
DEFAULT_UPDATE_INTERVAL_HOURS = 12
DEFAULT_TRACKED_FUNDS = [
    "BBVALIQ:B",
    "BBVARV:B",
    "BBVAGUB:C",
    "BBVAPC:C",
    "BBVAPCD:C",
]

BBVA_DEFAULT_PDF_URL = (
    "https://portal.bbva.mx/siabinternet/Repositorio/import/doctos/analisis/00003776.pdf"
)

# Entity Attributes
ATTR_REPORT_DATE = "report_date"
ATTR_RENDIMIENTO_DIARIO = "rendimiento_diario"
ATTR_RENDIMIENTO_SEMANAL = "rendimiento_semanal"
ATTR_RENDIMIENTO_MES = "rendimiento_mes"
ATTR_RENDIMIENTO_ANIO = "rendimiento_anio"
ATTR_RENDIMIENTO_1A = "rendimiento_1a"
ATTR_RENDIMIENTO_2A = "rendimiento_2a"
ATTR_CALIFICACION = "calificacion"
ATTR_MINIMO_INVERSION = "minimo_inversion"
ATTR_SEGMENT = "segment"
ATTR_CATEGORY = "category"
ATTR_SERIES = "series"
ATTR_TICKER = "ticker"
