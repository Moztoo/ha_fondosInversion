"""Pydantic models and API schemas conforming to backend skill guidelines.

Strict validation, standard envelope types, and error structures.
"""
from datetime import date, datetime
from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Core Domain Schemas
# ---------------------------------------------------------------------------

class RendimientoSnapshot(BaseModel):
    """Yields and price snapshot for a specific date."""
    model_config = ConfigDict(extra="forbid")

    report_date: str = Field(..., description="Report elaboration date (YYYY-MM-DD)")
    rendimiento_diario: Optional[float] = Field(None, description="Daily yield percentage")
    rendimiento_semanal: Optional[float] = Field(None, description="Weekly yield percentage")
    rendimiento_mes: Optional[float] = Field(None, description="Month-to-date yield percentage")
    rendimiento_anio: Optional[float] = Field(None, description="Year-to-date yield percentage")
    rendimiento_1a: Optional[float] = Field(None, description="1-year annualized yield percentage")
    rendimiento_2a: Optional[float] = Field(None, description="2-year annualized yield percentage")
    precio: float = Field(..., description="Share price in Mexican Pesos (MXN) or USD")

class FundSeriesRow(BaseModel):
    """Full flat row representation of a fund series with all Anaquel columns."""
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., description="Fund Ticker symbol (ej. BBVALIQ)")
    series: str = Field(..., description="Fund Series (ej. B, C, P)")
    segment: str = Field(..., description="Client segment: Personas Físicas, Personas Morales, Colaboradores")
    category: str = Field(..., description="Fund category")
    minimo_inversion: float = Field(0.0, description="Minimum investment amount")
    calificacion: Optional[str] = Field(None, description="Risk / Credit rating (ej. AAA/1, AA/3)")
    rendimiento_diario: Optional[float] = Field(None, description="Daily yield percentage")
    rendimiento_semanal: Optional[float] = Field(None, description="Weekly yield percentage")
    rendimiento_mes: Optional[float] = Field(None, description="Month-to-date yield percentage")
    rendimiento_anio: Optional[float] = Field(None, description="Year-to-date yield percentage")
    rendimiento_1a: Optional[float] = Field(None, description="1-year annualized yield percentage")
    rendimiento_2a: Optional[float] = Field(None, description="2-year annualized yield percentage")
    precio: float = Field(..., description="Share price")
    report_date: Optional[str] = Field(None, description="Report date YYYY-MM-DD")
    is_favorite: bool = Field(False, description="Whether this fund series is marked as favorite")

class FundSeriesDetail(BaseModel):
    """Detailed series metrics including latest snapshot and metadata."""
    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="Unique Series ID")
    ticker: str = Field(..., description="Fund Ticker symbol (e.g. BBVALIQ, BBVARV)")
    series: str = Field(..., description="Fund Series (e.g. B, C, P, PV, UHN)")
    segment: str = Field(..., description="Client segment: Personas Físicas, Personas Morales, Colaboradores")
    category: str = Field(..., description="Fund category: Fondos de Deuda, Renta Variable, etc.")
    minimo_inversion: float = Field(0.0, description="Minimum investment amount in currency")
    calificacion: Optional[str] = Field(None, description="Credit / Risk rating (e.g. AAA/1, AA/2)")
    is_favorite: bool = Field(False, description="Whether this fund series is marked as favorite")
    latest_snapshot: Optional[RendimientoSnapshot] = Field(None, description="Latest available yields and price")
    history_count: int = Field(0, description="Total historical snapshots recorded")

class FundSummary(BaseModel):
    """Aggregated fund view grouping series."""
    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(..., description="Fund Ticker symbol")
    name: Optional[str] = Field(None, description="Display name of the fund")
    category: str = Field(..., description="Category")
    segment: str = Field(..., description="Client segment")
    series_list: List[str] = Field(default_factory=list, description="Available series for this fund")
    latest_price: Optional[float] = Field(None, description="Latest price of primary/reference series")
    latest_rendimiento_1a: Optional[float] = Field(None, description="Latest 1-year yield of primary series")
    latest_report_date: Optional[str] = Field(None, description="Latest update date")

class HistoryFilterParams(BaseModel):
    """Query parameters to filter historical yield curves."""
    from_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    to_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    limit: int = Field(100, ge=1, le=1000, description="Maximum snapshots to return")

class SyncResult(BaseModel):
    """Outcome of a scraper synchronization run."""
    model_config = ConfigDict(extra="forbid")

    success: bool
    status: str
    report_date: Optional[str]
    total_parsed: int
    new_snapshots_inserted: int
    funds_updated: int
    duration_seconds: float
    message: str

class SystemHealth(BaseModel):
    """Health check payload for monitoring."""
    status: str
    version: str
    total_funds: int
    total_series: int
    total_snapshots: int
    last_report_date: Optional[str]
    last_sync_time: Optional[str]
    auto_sync_time: Optional[str] = "22:00"
    auto_sync_enabled: bool = True

class ToggleFavoriteResponse(BaseModel):
    """Response payload when toggling favorite status of a series."""
    ticker: str
    series: str
    is_favorite: bool
    message: str

class NotificationTestResponse(BaseModel):
    """Result of dispatching a test push notification to Home Assistant."""
    sent: bool
    event_fired: bool
    device: str
    favorites_count: int
    summary: str

# ---------------------------------------------------------------------------
# Standard Envelopes (Clean Architecture)
# ---------------------------------------------------------------------------

class ResponseMeta(BaseModel):
    """Standard metadata for list and pagination responses."""
    page: Optional[int] = None
    limit: Optional[int] = None
    total: Optional[int] = None
    filters: Optional[dict[str, Any]] = None

class StandardResponse(BaseModel, Generic[T]):
    """Standard success envelope conforming to backend skill standards."""
    success: bool = True
    data: T
    meta: Optional[ResponseMeta] = None

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: str

class ErrorPayload(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None

class StandardErrorResponse(BaseModel):
    """Standard error envelope conforming to backend skill standards."""
    success: bool = False
    error: ErrorPayload
