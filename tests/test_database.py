"""Unit tests for SQLite database and repository."""
import os
import tempfile
import pytest
from app.database import get_sync_connection, init_db
from app.parser import ParsedAnaquelReport, ParsedFundRecord
from app.repository import FondosRepository

@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_sqlite_pragmas_and_schema(temp_db):
    conn = get_sync_connection(temp_db)
    cur = conn.cursor()

    cur.execute("PRAGMA journal_mode")
    assert cur.fetchone()[0].lower() == "wal"

    cur.execute("PRAGMA foreign_keys")
    assert cur.fetchone()[0] == 1

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]
    assert "funds" in tables
    assert "fund_series" in tables
    assert "rendimientos_history" in tables
    assert "sync_logs" in tables
    conn.close()

def test_repository_upsert_and_query(temp_db):
    conn = get_sync_connection(temp_db)
    repo = FondosRepository(conn)

    report = ParsedAnaquelReport(
        report_date="2026-11-10",
        total_records=2,
        records=[
            ParsedFundRecord(
                ticker="TESTLIQ",
                series="B",
                segment="Personas Físicas",
                category="Fondos de Deuda",
                minimo_inversion=1000.0,
                calificacion="AAA/1",
                rendimiento_diario=4.5,
                rendimiento_semanal=4.6,
                rendimiento_mes=4.7,
                rendimiento_anio=4.8,
                rendimiento_1a=5.0,
                rendimiento_2a=6.0,
                precio=20.5,
                report_date="2026-11-10",
            ),
            ParsedFundRecord(
                ticker="TESTLIQ",
                series="C",
                segment="Personas Físicas",
                category="Fondos de Deuda",
                minimo_inversion=50000.0,
                calificacion="AAA/1",
                rendimiento_diario=4.7,
                rendimiento_semanal=4.8,
                rendimiento_mes=4.9,
                rendimiento_anio=5.0,
                rendimiento_1a=5.2,
                rendimiento_2a=6.2,
                precio=21.0,
                report_date="2026-11-10",
            ),
        ],
    )

    stats = repo.upsert_parsed_report(report)
    assert stats["funds_upserted"] == 1
    assert stats["series_upserted"] == 2
    assert stats["snapshots_inserted"] == 2

    # Query funds
    funds, total = repo.list_funds(search="TESTLIQ")
    assert total == 1
    assert funds[0]["ticker"] == "TESTLIQ"
    assert "B" in funds[0]["series_list"]
    assert "C" in funds[0]["series_list"]

    # Query history
    history = repo.get_series_history("TESTLIQ", "B")
    assert len(history) == 1
    assert history[0]["precio"] == 20.5
    assert history[0]["rendimiento_1a"] == 5.0
    conn.close()
