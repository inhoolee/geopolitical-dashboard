"""DuckDB read-only connection for the dashboard (cached across reruns)."""

from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent.parent / "data" / "warehouse" / "geopolitical.duckdb"


@st.cache_resource
def get_conn() -> duckdb.DuckDBPyConnection:
    """Single persistent read-only connection, shared across all reruns."""
    if not DB_PATH.exists():
        st.error(f"Database not found: {DB_PATH}\nRun the pipeline first.")
        st.stop()
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(ttl=3600, show_spinner=False)
def query(_conn, sql: str, params: list | None = None) -> pd.DataFrame:
    """Execute SQL and return a DataFrame; cached for 1 hour."""
    if params:
        return _conn.execute(sql, params).df()
    return _conn.execute(sql).df()
