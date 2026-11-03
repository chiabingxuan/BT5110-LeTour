"""Database access: one shared engine and cached SELECTs."""
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


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


@st.cache_data(show_spinner=False)
def query(sql, **params):
    """Runs a SELECT and returns a DataFrame. Results are cached per SQL text and parameters."""
    with engine().connect() as connection:
        return pd.read_sql(text(sql), connection, params=params)
