"""Service layer orchestrating scraper, parser, and persistence logic."""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.database import get_sync_connection
from app.config import settings
from app.models import (
    FundSeriesDetail,
    FundSeriesRow,
    FundSummary,
    RendimientoSnapshot,
    SyncResult,
    SystemHealth,
)
from app.parser import AnaquelParser
from app.repository import FondosRepository
from app.scraper import BBVAScraper
from app.ha_client import HomeAssistantClient

logger = logging.getLogger("bbva_fondos.service")

class FondosService:
    """Core domain service for funds management."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.scraper = BBVAScraper()
        self.parser = AnaquelParser()
        self.ha_client = HomeAssistantClient()

    def sync_data(self, custom_pdf_bytes: Optional[bytes] = None) -> SyncResult:
        """Download (or accept) PDF, parse records, and persist to database."""
        start_time = time.time()
        conn = get_sync_connection(self.db_path)
        repo = FondosRepository(conn)
        log_id = repo.start_sync_log()

        try:
            if custom_pdf_bytes:
                pdf_bytes = custom_pdf_bytes
                source = "custom_upload"
            else:
                pdf_bytes, source = self.scraper.fetch_pdf_bytes_sync()

            report = self.parser.parse_pdf(pdf_bytes)
            if report.total_records == 0:
                raise ValueError("Parsed PDF contained 0 fund records")

            stats = repo.upsert_parsed_report(report)
            repo.finish_sync_log(
                log_id=log_id,
                status="SUCCESS",
                report_date=report.report_date,
                total_parsed=report.total_records,
            )

            duration = round(time.time() - start_time, 2)
            msg = (
                f"Successfully synced {report.total_records} records for date {report.report_date} "
                f"({stats['funds_upserted']} funds added, {stats['snapshots_inserted']} snapshots saved) in {duration}s"
            )
            logger.info(msg)

            # Dispatch notification & signal to Home Assistant for favorite funds
            try:
                self.dispatch_favorites_notification(report_date=report.report_date)
            except Exception as notify_err:
                logger.warning("Failed to dispatch favorites notification: %s", notify_err)

            return SyncResult(
                success=True,
                status="SUCCESS",
                report_date=report.report_date,
                total_parsed=report.total_records,
                new_snapshots_inserted=stats["snapshots_inserted"],
                funds_updated=stats["funds_upserted"],
                duration_seconds=duration,
                message=msg,
            )
        except Exception as e:
            conn.rollback()
            err_msg = str(e)
            repo.finish_sync_log(log_id=log_id, status="FAILED", error_msg=err_msg)
            duration = round(time.time() - start_time, 2)
            logger.exception("Synchronization failed: %s", err_msg)
            return SyncResult(
                success=False,
                status="FAILED",
                report_date=None,
                total_parsed=0,
                new_snapshots_inserted=0,
                funds_updated=0,
                duration_seconds=duration,
                message=f"Sync error: {err_msg}",
            )
        finally:
            conn.close()

    def get_series_catalog(
        self,
        segment: Optional[str] = None,
        category: Optional[str] = None,
        is_debt_only: bool = False,
        only_favorites: bool = False,
        search: Optional[str] = None,
        sort_by: str = "ticker",
        order: str = "ASC",
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[FundSeriesRow], int]:
        """Retrieve paginated list of all individual fund series with all columns."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            raw_series, total = repo.list_all_series(
                segment=segment,
                category=category,
                is_debt_only=is_debt_only,
                only_favorites=only_favorites,
                search=search,
                sort_by=sort_by,
                order=order,
                page=page,
                limit=limit,
            )
            result = [
                FundSeriesRow(
                    ticker=r["ticker"],
                    series=r["series"],
                    segment=r["segment"],
                    category=r["category"],
                    minimo_inversion=r["minimo_inversion"],
                    calificacion=r["calificacion"],
                    rendimiento_diario=r["rendimiento_diario"],
                    rendimiento_semanal=r["rendimiento_semanal"],
                    rendimiento_mes=r["rendimiento_mes"],
                    rendimiento_anio=r["rendimiento_anio"],
                    rendimiento_1a=r["rendimiento_1a"],
                    rendimiento_2a=r["rendimiento_2a"],
                    precio=r["precio"],
                    report_date=r["report_date"],
                    is_favorite=bool(r.get("is_favorite", False)),
                )
                for r in raw_series
            ]
            return result, total
        finally:
            conn.close()

    def get_funds(
        self,
        segment: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 100,
    ) -> Tuple[List[FundSummary], int]:
        """Retrieve paginated list of funds."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            raw_funds, total = repo.list_funds(
                segment=segment,
                category=category,
                search=search,
                page=page,
                limit=limit,
            )
            funds = [FundSummary(**f) for f in raw_funds]
            return funds, total
        finally:
            conn.close()

    def get_fund_series(self, ticker: str, segment: Optional[str] = None) -> List[FundSeriesDetail]:
        """Retrieve all series of a fund."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            raw_series = repo.get_fund_series_list(ticker=ticker, segment=segment)
            result = []
            for s in raw_series:
                latest_snap = (
                    RendimientoSnapshot(**s["latest_snapshot"])
                    if s["latest_snapshot"]
                    else None
                )
                result.append(
                    FundSeriesDetail(
                        id=s["id"],
                        ticker=s["ticker"],
                        series=s["series"],
                        segment=s["segment"],
                        category=s["category"],
                        minimo_inversion=s["minimo_inversion"],
                        calificacion=s["calificacion"],
                        history_count=s["history_count"],
                        latest_snapshot=latest_snap,
                    )
                )
            return result
        finally:
            conn.close()

    def get_history(
        self,
        ticker: str,
        series: str,
        segment: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 365,
    ) -> List[RendimientoSnapshot]:
        """Retrieve historical yield snapshots."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            raw_history = repo.get_series_history(
                ticker=ticker,
                series=series,
                segment=segment,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
            )
            return [RendimientoSnapshot(**h) for h in raw_history]
        finally:
            conn.close()

    def get_filters(self) -> Dict[str, List[str]]:
        """Retrieve distinct segments and categories."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            return repo.get_all_segments_and_categories()
        finally:
            conn.close()

    def toggle_favorite(self, ticker: str, series: str) -> Optional[bool]:
        """Toggle favorite state of a fund series."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            return repo.toggle_favorite(ticker=ticker, series=series)
        finally:
            conn.close()

    def get_favorites(self) -> List[Dict[str, Any]]:
        """Retrieve list of favorite fund series with current yields."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            return repo.get_favorites()
        finally:
            conn.close()

    def dispatch_favorites_notification(
        self, report_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract favorites and send push notification and signal to Home Assistant."""
        favorites = self.get_favorites()
        return self.ha_client.notify_favorites_update(
            favorites=favorites, report_date=report_date
        )

    def test_notification(self) -> Dict[str, Any]:
        """Send a test push notification to Home Assistant device to verify setup."""
        favorites = self.get_favorites()
        if not favorites:
            # Create a sample test payload so user can test the push alert immediately
            sample_fav = [
                {
                    "ticker": "BBVALIQ",
                    "series": "C",
                    "fund_name": "Fondo BBVALIQ",
                    "category": "Fondos de Deuda",
                    "segment": "Personas Físicas",
                    "rendimiento_mes": 0.89,
                    "precio": 12.3456,
                    "report_date": "Prueba",
                }
            ]
            return self.ha_client.notify_favorites_update(
                favorites=sample_fav, report_date="Notificación de Prueba"
            )
        return self.ha_client.notify_favorites_update(
            favorites=favorites, report_date="Prueba Manual"
        )

    def get_health(self) -> SystemHealth:
        """Retrieve system telemetry and record counts."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            stats = repo.get_system_stats()
            return SystemHealth(
                status="healthy",
                version="1.0.5",
                total_funds=stats["total_funds"],
                total_series=stats["total_series"],
                total_snapshots=stats["total_snapshots"],
                last_report_date=stats["last_report_date"],
                last_sync_time=stats["last_sync_time"],
                auto_sync_time=settings.AUTO_SYNC_TIME,
                auto_sync_enabled=settings.AUTO_SYNC_ENABLED,
            )
        finally:
            conn.close()
