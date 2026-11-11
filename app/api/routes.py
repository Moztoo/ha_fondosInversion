"""FastAPI API routes conforming to backend skill standards.

Standard envelopes, typed Pydantic v2 schemas, predictable error codes.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.models import (
    ErrorPayload,
    FundSeriesDetail,
    FundSummary,
    RendimientoSnapshot,
    ResponseMeta,
    StandardErrorResponse,
    StandardResponse,
    SyncResult,
    SystemHealth,
)
from app.service import FondosService

router = APIRouter(prefix="/api/v1", tags=["BBVA Fondos"])
service = FondosService()

@router.get(
    "/health",
    response_model=StandardResponse[SystemHealth],
    summary="System Health & Database Statistics",
    description="Check operational health, database record counts, and last sync timestamp.",
)
def get_health():
    health = service.get_health()
    return StandardResponse(data=health)

@router.get(
    "/filters",
    response_model=StandardResponse[dict],
    summary="Filter Options",
    description="Retrieve available customer segments and fund categories.",
)
def get_filters():
    data = service.get_filters()
    return StandardResponse(data=data)

@router.get(
    "/funds",
    response_model=StandardResponse[List[FundSummary]],
    summary="List BBVA Funds",
    description="Retrieve paginated list of funds with current reference metrics, search, and segment/category filters.",
)
def list_funds(
    segment: Optional[str] = Query(None, description="Filter by segment (Personas Físicas, Personas Morales, Colaboradores BBVA)"),
    category: Optional[str] = Query(None, description="Filter by fund category"),
    search: Optional[str] = Query(None, description="Search ticker or fund name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
):
    funds, total = service.get_funds(
        segment=segment,
        category=category,
        search=search,
        page=page,
        limit=limit,
    )
    meta = ResponseMeta(
        page=page,
        limit=limit,
        total=total,
        filters={"segment": segment, "category": category, "search": search},
    )
    return StandardResponse(data=funds, meta=meta)

@router.get(
    "/funds/{ticker}",
    response_model=StandardResponse[List[FundSeriesDetail]],
    summary="Fund Series & Latest Snapshots",
    description="Retrieve all series, minimum investments, ratings, and latest price/yields for a specific fund ticker.",
)
def get_fund_series(
    ticker: str,
    segment: Optional[str] = Query(None, description="Optional filter by segment"),
):
    series_list = service.get_fund_series(ticker=ticker, segment=segment)
    if not series_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "FUND_NOT_FOUND",
                "message": f"No fund series found matching ticker '{ticker.upper()}'.",
            },
        )
    return StandardResponse(data=series_list, meta=ResponseMeta(total=len(series_list)))

@router.get(
    "/funds/{ticker}/{series}",
    response_model=StandardResponse[FundSeriesDetail],
    summary="Specific Fund Series Detail",
    description="Retrieve metadata and latest performance snapshot for an exact fund ticker and series.",
)
def get_series_detail(
    ticker: str,
    series: str,
    segment: Optional[str] = Query(None, description="Optional segment"),
):
    series_list = service.get_fund_series(ticker=ticker, segment=segment)
    matching = [s for s in series_list if s.series.upper() == series.upper()]
    if not matching:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "SERIES_NOT_FOUND",
                "message": f"Series '{series.upper()}' for ticker '{ticker.upper()}' not found.",
            },
        )
    return StandardResponse(data=matching[0])

@router.get(
    "/funds/{ticker}/{series}/history",
    response_model=StandardResponse[List[RendimientoSnapshot]],
    summary="Historical Performance Timeline",
    description="Retrieve historical time-series of prices and yields for charting and external consumption.",
)
def get_series_history(
    ticker: str,
    series: str,
    segment: Optional[str] = Query(None, description="Optional segment"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(365, ge=1, le=1000, description="Max snapshots"),
):
    history = service.get_history(
        ticker=ticker,
        series=series,
        segment=segment,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )
    if not history:
        # Check if the series exists
        series_list = service.get_fund_series(ticker=ticker, segment=segment)
        matching = [s for s in series_list if s.series.upper() == series.upper()]
        if not matching:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "SERIES_NOT_FOUND",
                    "message": f"Series '{series.upper()}' for ticker '{ticker.upper()}' not found.",
                },
            )
    return StandardResponse(data=history, meta=ResponseMeta(total=len(history)))

@router.post(
    "/sync",
    response_model=StandardResponse[SyncResult],
    summary="Trigger Anaquel PDF Synchronization",
    description="Fetch the latest PDF from BBVA web repository, parse funds and persist snapshots.",
)
def trigger_sync():
    result = service.sync_data()
    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "code": "SYNC_FAILED",
                "message": result.message,
            },
        )
    return StandardResponse(data=result)
