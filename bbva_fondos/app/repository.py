"""Repository layer for SQLite persistence adhering to database-architect principles.

Ensures idempotent upserts, foreign-key consistency, and optimized index utilization.
"""
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from app.parser import ParsedAnaquelReport, ParsedFundRecord

class FondosRepository:
    """Data Access Object for Funds, Series, Snapshots and Sync Logs."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert_parsed_report(self, report: ParsedAnaquelReport) -> Dict[str, int]:
        """Atomically persist parsed funds, series, and historical rendimientos."""
        cur = self.conn.cursor()
        funds_upserted = 0
        series_upserted = 0
        snapshots_inserted = 0

        # Cache fund and series IDs to avoid redundant lookups
        # Map: (ticker, segment, category) -> fund_id
        fund_cache: Dict[Tuple[str, str, str], int] = {}
        # Map: (fund_id, series) -> series_id
        series_cache: Dict[Tuple[int, str], int] = {}

        # Preload existing funds
        cur.execute("SELECT id, ticker, segment, category FROM funds")
        for row in cur.fetchall():
            fund_cache[(row["ticker"], row["segment"], row["category"])] = row["id"]

        # Preload existing series
        cur.execute("SELECT id, fund_id, series FROM fund_series")
        for row in cur.fetchall():
            series_cache[(row["fund_id"], row["series"])] = row["id"]

        for rec in report.records:
            fund_key = (rec.ticker, rec.segment, rec.category)
            fund_id = fund_cache.get(fund_key)

            if fund_id is None:
                cur.execute(
                    """
                    INSERT INTO funds (ticker, name, category, segment, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(ticker, segment, category) DO UPDATE SET
                        updated_at = datetime('now')
                    RETURNING id
                    """,
                    (rec.ticker, f"Fondo {rec.ticker}", rec.category, rec.segment),
                )
                res = cur.fetchone()
                fund_id = res["id"] if res else None
                if fund_id:
                    fund_cache[fund_key] = fund_id
                    funds_upserted += 1

            if not fund_id:
                continue

            # Upsert Series
            series_key = (fund_id, rec.series)
            series_id = series_cache.get(series_key)

            if series_id is None:
                cur.execute(
                    """
                    INSERT INTO fund_series (fund_id, series, minimo_inversion, calificacion, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(fund_id, series) DO UPDATE SET
                        minimo_inversion = excluded.minimo_inversion,
                        calificacion = excluded.calificacion,
                        updated_at = datetime('now')
                    RETURNING id
                    """,
                    (fund_id, rec.series, rec.minimo_inversion, rec.calificacion),
                )
                res = cur.fetchone()
                series_id = res["id"] if res else None
                if series_id:
                    series_cache[series_key] = series_id
                    series_upserted += 1
            else:
                # Update series metadata if changed
                cur.execute(
                    """
                    UPDATE fund_series
                    SET minimo_inversion = ?, calificacion = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (rec.minimo_inversion, rec.calificacion, series_id),
                )

            if not series_id:
                continue

            # Upsert Historical Rendimiento Snapshot
            cur.execute(
                """
                INSERT INTO rendimientos_history (
                    fund_series_id, report_date,
                    rendimiento_diario, rendimiento_semanal, rendimiento_mes,
                    rendimiento_anio, rendimiento_1a, rendimiento_2a,
                    precio, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(fund_series_id, report_date) DO UPDATE SET
                    rendimiento_diario = excluded.rendimiento_diario,
                    rendimiento_semanal = excluded.rendimiento_semanal,
                    rendimiento_mes = excluded.rendimiento_mes,
                    rendimiento_anio = excluded.rendimiento_anio,
                    rendimiento_1a = excluded.rendimiento_1a,
                    rendimiento_2a = excluded.rendimiento_2a,
                    precio = excluded.precio
                """,
                (
                    series_id,
                    rec.report_date,
                    rec.rendimiento_diario,
                    rec.rendimiento_semanal,
                    rec.rendimiento_mes,
                    rec.rendimiento_anio,
                    rec.rendimiento_1a,
                    rec.rendimiento_2a,
                    rec.precio,
                ),
            )
            snapshots_inserted += 1

        self.conn.commit()
        return {
            "funds_upserted": funds_upserted,
            "series_upserted": series_upserted,
            "snapshots_inserted": snapshots_inserted,
        }

    def list_all_series(
        self,
        segment: Optional[str] = None,
        category: Optional[str] = None,
        is_debt_only: bool = False,
        search: Optional[str] = None,
        sort_by: str = "ticker",
        order: str = "ASC",
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List all individual fund series with all columns and current snapshot."""
        cur = self.conn.cursor()
        where_clauses = ["1=1"]
        params: List[Any] = []

        if segment:
            where_clauses.append("f.segment = ?")
            params.append(segment)
        if category:
            where_clauses.append("f.category = ?")
            params.append(category)
        if is_debt_only:
            where_clauses.append("(f.category LIKE '%Deuda%' OR f.category LIKE '%Divisas%' OR f.category LIKE '%Estrategias%') AND f.category NOT LIKE '%Renta Variable%'")
        if search:
            where_clauses.append("(f.ticker LIKE ? OR fs.series LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_str = " AND ".join(where_clauses)

        # Count total
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM fund_series fs
            JOIN funds f ON f.id = fs.fund_id
            WHERE {where_str}
        """
        cur.execute(count_sql, params)
        total = cur.fetchone()["total"]

        # Validate sorting
        valid_sort_cols = {
            "ticker": "f.ticker",
            "series": "fs.series",
            "precio": "rh.precio",
            "rendimiento_diario": "rh.rendimiento_diario",
            "rendimiento_semanal": "rh.rendimiento_semanal",
            "rendimiento_mes": "rh.rendimiento_mes",
            "rendimiento_anio": "rh.rendimiento_anio",
            "rendimiento_1a": "rh.rendimiento_1a",
            "rendimiento_2a": "rh.rendimiento_2a",
            "minimo_inversion": "fs.minimo_inversion",
            "calificacion": "fs.calificacion",
        }
        sort_column = valid_sort_cols.get(sort_by.lower(), "f.ticker")
        sort_order = "DESC" if order.upper() == "DESC" else "ASC"

        offset = (page - 1) * limit
        sql = f"""
            SELECT 
                fs.id as series_id,
                f.ticker,
                fs.series,
                f.segment,
                f.category,
                fs.minimo_inversion,
                fs.calificacion,
                rh.rendimiento_diario,
                rh.rendimiento_semanal,
                rh.rendimiento_mes,
                rh.rendimiento_anio,
                rh.rendimiento_1a,
                rh.rendimiento_2a,
                rh.precio,
                rh.report_date,
                (
                    SELECT COUNT(*) FROM rendimientos_history rh_cnt 
                    WHERE rh_cnt.fund_series_id = fs.id
                ) as history_count
            FROM fund_series fs
            JOIN funds f ON f.id = fs.fund_id
            LEFT JOIN rendimientos_history rh ON rh.fund_series_id = fs.id 
                AND rh.report_date = (
                    SELECT MAX(rh_inner.report_date) 
                    FROM rendimientos_history rh_inner 
                    WHERE rh_inner.fund_series_id = fs.id
                )
            WHERE {where_str}
            ORDER BY {sort_column} {sort_order}, fs.series ASC
            LIMIT ? OFFSET ?
        """
        cur.execute(sql, params + [limit, offset])
        rows = [dict(r) for r in cur.fetchall()]
        return rows, total

    def list_funds(
        self,
        segment: Optional[str] = None,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List funds with latest performance snapshot and aggregated series."""
        cur = self.conn.cursor()

        where_clauses = ["1=1"]
        params: List[Any] = []

        if segment:
            where_clauses.append("f.segment = ?")
            params.append(segment)
        if category:
            where_clauses.append("f.category = ?")
            params.append(category)
        if search:
            where_clauses.append("(f.ticker LIKE ? OR f.name LIKE ?)")
            params.extend([f"%{search}%", f"%{search}%"])

        where_str = " AND ".join(where_clauses)

        # Count total matching
        count_sql = f"SELECT COUNT(DISTINCT f.id) as total FROM funds f WHERE {where_str}"
        cur.execute(count_sql, params)
        total = cur.fetchone()["total"]

        offset = (page - 1) * limit
        sql = f"""
            SELECT 
                f.id,
                f.ticker,
                f.name,
                f.category,
                f.segment,
                GROUP_CONCAT(DISTINCT fs.series) as series_list,
                MAX(rh.report_date) as latest_report_date
            FROM funds f
            LEFT JOIN fund_series fs ON fs.fund_id = f.id
            LEFT JOIN rendimientos_history rh ON rh.fund_series_id = fs.id
            WHERE {where_str}
            GROUP BY f.id, f.ticker, f.name, f.category, f.segment
            ORDER BY f.ticker ASC
            LIMIT ? OFFSET ?
        """
        cur.execute(sql, params + [limit, offset])
        rows = cur.fetchall()

        funds = []
        for r in rows:
            series_str = r["series_list"] or ""
            series_arr = sorted(list(set(series_str.split(",")))) if series_str else []

            # Fetch representative latest price & yield from first series or highest volume
            latest_price = None
            latest_rend_1a = None
            if r["id"]:
                cur.execute(
                    """
                    SELECT rh.precio, rh.rendimiento_1a, rh.rendimiento_diario
                    FROM fund_series fs
                    JOIN rendimientos_history rh ON rh.fund_series_id = fs.id
                    WHERE fs.fund_id = ?
                    ORDER BY rh.report_date DESC, fs.minimo_inversion ASC
                    LIMIT 1
                    """,
                    (r["id"],),
                )
                sample = cur.fetchone()
                if sample:
                    latest_price = sample["precio"]
                    latest_rend_1a = sample["rendimiento_1a"]

            funds.append({
                "ticker": r["ticker"],
                "name": r["name"],
                "category": r["category"],
                "segment": r["segment"],
                "series_list": series_arr,
                "latest_price": latest_price,
                "latest_rendimiento_1a": latest_rend_1a,
                "latest_report_date": r["latest_report_date"],
            })

        return funds, total

    def get_fund_series_list(self, ticker: str, segment: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all series for a specific ticker symbol with their latest snapshot."""
        cur = self.conn.cursor()
        query = """
            SELECT 
                fs.id as series_id,
                f.ticker,
                fs.series,
                f.segment,
                f.category,
                fs.minimo_inversion,
                fs.calificacion,
                (
                    SELECT COUNT(*) FROM rendimientos_history rh_cnt 
                    WHERE rh_cnt.fund_series_id = fs.id
                ) as history_count
            FROM fund_series fs
            JOIN funds f ON f.id = fs.fund_id
            WHERE UPPER(f.ticker) = UPPER(?)
        """
        params = [ticker]
        if segment:
            query += " AND f.segment = ?"
            params.append(segment)
        query += " ORDER BY f.segment ASC, fs.series ASC"

        cur.execute(query, params)
        rows = cur.fetchall()

        result = []
        for r in rows:
            # Get latest snapshot
            cur.execute(
                """
                SELECT report_date, rendimiento_diario, rendimiento_semanal, 
                       rendimiento_mes, rendimiento_anio, rendimiento_1a, rendimiento_2a, precio
                FROM rendimientos_history
                WHERE fund_series_id = ?
                ORDER BY report_date DESC
                LIMIT 1
                """,
                (r["series_id"],),
            )
            latest = cur.fetchone()
            latest_dict = dict(latest) if latest else None

            result.append({
                "id": r["series_id"],
                "ticker": r["ticker"],
                "series": r["series"],
                "segment": r["segment"],
                "category": r["category"],
                "minimo_inversion": r["minimo_inversion"],
                "calificacion": r["calificacion"],
                "history_count": r["history_count"],
                "latest_snapshot": latest_dict,
            })

        return result

    def get_series_history(
        self,
        ticker: str,
        series: str,
        segment: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 365,
    ) -> List[Dict[str, Any]]:
        """Retrieve historical timeline of yields and prices for a series."""
        cur = self.conn.cursor()
        clauses = [
            "UPPER(f.ticker) = UPPER(?)",
            "UPPER(fs.series) = UPPER(?)",
        ]
        params: List[Any] = [ticker, series]

        if segment:
            clauses.append("f.segment = ?")
            params.append(segment)
        if from_date:
            clauses.append("rh.report_date >= ?")
            params.append(from_date)
        if to_date:
            clauses.append("rh.report_date <= ?")
            params.append(to_date)

        where_sql = " AND ".join(clauses)
        sql = f"""
            SELECT 
                rh.report_date,
                rh.rendimiento_diario,
                rh.rendimiento_semanal,
                rh.rendimiento_mes,
                rh.rendimiento_anio,
                rh.rendimiento_1a,
                rh.rendimiento_2a,
                rh.precio
            FROM rendimientos_history rh
            JOIN fund_series fs ON fs.id = rh.fund_series_id
            JOIN funds f ON f.id = fs.fund_id
            WHERE {where_sql}
            ORDER BY rh.report_date ASC
            LIMIT ?
        """
        cur.execute(sql, params + [limit])
        return [dict(row) for row in cur.fetchall()]

    def get_all_segments_and_categories(self) -> Dict[str, List[str]]:
        """Return distinct segments and categories for UI filter chips."""
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT segment FROM funds ORDER BY segment")
        segments = [r["segment"] for r in cur.fetchall()]

        cur.execute("SELECT DISTINCT category FROM funds ORDER BY category")
        categories = [r["category"] for r in cur.fetchall()]

        return {"segments": segments, "categories": categories}

    def get_system_stats(self) -> Dict[str, Any]:
        """Return system telemetry and record counts."""
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) as c FROM funds")
        total_funds = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM fund_series")
        total_series = cur.fetchone()["c"]

        cur.execute("SELECT COUNT(*) as c FROM rendimientos_history")
        total_snapshots = cur.fetchone()["c"]

        cur.execute("SELECT MAX(report_date) as last_date FROM rendimientos_history")
        last_date = cur.fetchone()["last_date"]

        cur.execute("SELECT MAX(started_at) as last_sync FROM sync_logs WHERE status = 'SUCCESS'")
        last_sync = cur.fetchone()["last_sync"]

        return {
            "total_funds": total_funds,
            "total_series": total_series,
            "total_snapshots": total_snapshots,
            "last_report_date": last_date,
            "last_sync_time": last_sync,
        }

    def start_sync_log(self) -> int:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO sync_logs (status) VALUES ('RUNNING') RETURNING id")
        log_id = cur.fetchone()["id"]
        self.conn.commit()
        return log_id

    def finish_sync_log(
        self,
        log_id: int,
        status: str,
        report_date: Optional[str] = None,
        total_parsed: int = 0,
        error_msg: Optional[str] = None,
    ) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE sync_logs
            SET finished_at = datetime('now'),
                status = ?,
                report_date = ?,
                total_series_parsed = ?,
                error_message = ?
            WHERE id = ?
            """,
            (status, report_date, total_parsed, error_msg, log_id),
        )
        self.conn.commit()
