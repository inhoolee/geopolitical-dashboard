"""DuckDB connection factory and schema bootstrapper."""

import logging
from pathlib import Path

import duckdb

from pipeline.config import WAREHOUSE_PATH, SQL_SCHEMA_DIR

logger = logging.getLogger(__name__)


def get_connection(path: Path | None = None) -> duckdb.DuckDBPyConnection:
    """Return a persistent connection to the warehouse file."""
    target = path or WAREHOUSE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(target))


def get_memory_connection() -> duckdb.DuckDBPyConnection:
    """Return an in-memory connection (for tests)."""
    return duckdb.connect(":memory:")


def bootstrap_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Apply all sql/schema/*.sql files then sql/queries/*.sql files in alphabetical order."""
    from pipeline.config import SQL_QUERIES_DIR
    sql_files = sorted(SQL_SCHEMA_DIR.glob("*.sql")) + sorted(SQL_QUERIES_DIR.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"No SQL schema files found in {SQL_SCHEMA_DIR}")
    for sql_file in sql_files:
        logger.info("Applying schema: %s", sql_file.name)
        conn.execute(sql_file.read_text())
    conn.commit()
    logger.info("Schema bootstrap complete (%d files applied)", len(sql_files))
