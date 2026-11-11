"""Database module conforming to database-architect skill standards.

Configures SQLite WAL mode, foreign keys, busy timeout, and schema DDL.
Supports both asynchronous (aiosqlite) and synchronous (sqlite3) operations.
"""
import os
import sqlite3
from pathlib import Path
from typing import AsyncGenerator
import aiosqlite

from app.config import settings

SQLITE_PRAGMAS = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
"""

SCHEMA_DDL = """
-- Table: funds
CREATE TABLE IF NOT EXISTS funds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    name TEXT,
    category TEXT NOT NULL,
    segment TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(ticker, segment, category)
);

-- Table: fund_series
CREATE TABLE IF NOT EXISTS fund_series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_id INTEGER NOT NULL,
    series TEXT NOT NULL,
    minimo_inversion REAL NOT NULL DEFAULT 0,
    calificacion TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(fund_id) REFERENCES funds(id) ON DELETE CASCADE,
    UNIQUE(fund_id, series)
);

-- Table: rendimientos_history
CREATE TABLE IF NOT EXISTS rendimientos_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fund_series_id INTEGER NOT NULL,
    report_date TEXT NOT NULL, -- YYYY-MM-DD
    rendimiento_diario REAL,
    rendimiento_semanal REAL,
    rendimiento_mes REAL,
    rendimiento_anio REAL,
    rendimiento_1a REAL,
    rendimiento_2a REAL,
    precio REAL NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(fund_series_id) REFERENCES fund_series(id) ON DELETE CASCADE,
    UNIQUE(fund_series_id, report_date)
);

-- Table: sync_logs
CREATE TABLE IF NOT EXISTS sync_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    report_date TEXT,
    total_series_parsed INTEGER DEFAULT 0,
    status TEXT NOT NULL, -- SUCCESS, FAILED, RUNNING
    error_message TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for high-speed queries and joins
CREATE INDEX IF NOT EXISTS idx_funds_ticker ON funds(ticker);
CREATE INDEX IF NOT EXISTS idx_funds_segment_cat ON funds(segment, category);
CREATE INDEX IF NOT EXISTS idx_fund_series_fid ON fund_series(fund_id);
CREATE INDEX IF NOT EXISTS idx_rendimientos_date ON rendimientos_history(report_date DESC);
CREATE INDEX IF NOT EXISTS idx_rendimientos_series_date ON rendimientos_history(fund_series_id, report_date DESC);
CREATE INDEX IF NOT EXISTS idx_sync_logs_started ON sync_logs(started_at DESC);
"""

def init_db(db_path: str | None = None) -> None:
    """Initialize SQLite database with WAL pragmas and schema synchronously."""
    path = db_path or settings.DATABASE_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    
    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        # Execute pragmas
        for line in SQLITE_PRAGMAS.strip().split(";"):
            stmt = line.strip()
            if stmt:
                conn.execute(stmt)
        # Execute schema
        conn.executescript(SCHEMA_DDL)
        conn.commit()

def get_sync_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Return a synchronous SQLite connection with pragmas applied."""
    path = db_path or settings.DATABASE_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    for line in SQLITE_PRAGMAS.strip().split(";"):
        stmt = line.strip()
        if stmt:
            conn.execute(stmt)
    return conn

async def get_async_connection(db_path: str | None = None) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide an aiosqlite connection dependency for FastAPI handlers."""
    path = db_path or settings.DATABASE_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(path)
    conn.row_factory = aiosqlite.Row
    for line in SQLITE_PRAGMAS.strip().split(";"):
        stmt = line.strip()
        if stmt:
            await conn.execute(stmt)
    try:
        yield conn
    finally:
        await conn.close()
