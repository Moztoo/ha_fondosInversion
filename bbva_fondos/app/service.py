"""Service layer orchestrating scraper, parser, and persistence logic."""
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from app.database import get_sync_connection
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

logger = logging.getLogger("bbva_fondos.service")

class FondosService:
    """Core domain service for funds management."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.scraper = BBVAScraper()
        self.parser = AnaquelParser()

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

    def get_health(self) -> SystemHealth:
        """Retrieve system telemetry and record counts."""
        conn = get_sync_connection(self.db_path)
        try:
            repo = FondosRepository(conn)
            stats = repo.get_system_stats()
            return SystemHealth(
                status="healthy",
                version="1.0.0",
                total_funds=stats["total_funds"],
                total_series=stats["total_series"],
                total_snapshots=stats["total_snapshots"],
                last_report_date=stats["last_report_date"],
                last_sync_time=stats["last_sync_time"],
            )
        finally:
            conn.close()
