"""Database access: one shared engine and cached SELECTs."""
import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

# init_db.py lives in src/; it owns the list of view files and the rebuild logic
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import init_db  # noqa: E402


@st.cache_resource
def engine():
    return create_engine(URL.create(
        "postgresql+psycopg2",
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        database=os.environ["DB_NAME"],
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    ))


@st.cache_resource(show_spinner="Updating the database views to match this version of the code…")
def ensure_current_views():
    """Runs once per app start: rebuilds the analytics views if the SQL files changed since they were installed."""
    connection = engine().raw_connection()
    try:
        with connection.cursor() as cursor:
            rebuilt = init_db.refresh_views_if_stale(cursor)
        connection.commit()
    finally:
        connection.close()
    if rebuilt:
        query.clear()
    return rebuilt


@st.cache_data(show_spinner=False)
def query(sql, **params):
    """Runs a SELECT and returns a DataFrame. Results are cached per SQL text and parameters."""
    with engine().connect() as connection:
        return pd.read_sql(text(sql), connection, params=params)
