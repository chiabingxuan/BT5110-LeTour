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


def setting(key, default=None):
    """A connection setting: from .env when running locally, else from Streamlit secrets (Streamlit Community Cloud)."""
    if key in os.environ:
        return os.environ[key]
    try:
        return st.secrets[key]
    except Exception:  # no secrets file, or the key is not in it
        if default is not None:
            return default
        raise KeyError(f"{key} is not set: add it to .env (local) or to the app's secrets (Streamlit Cloud)")


@st.cache_resource
def engine():
    # A hosted database such as Neon needs DB_SSLMODE=require; locally it is usually left unset
    sslmode = setting("DB_SSLMODE", "")
    return create_engine(URL.create(
        "postgresql+psycopg2",
        host=setting("DB_HOST"),
        port=int(setting("DB_PORT", "5432")),
        database=setting("DB_NAME"),
        username=setting("DB_USER"),
        password=setting("DB_PASSWORD"),
        query={"sslmode": sslmode} if sslmode else {},
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
