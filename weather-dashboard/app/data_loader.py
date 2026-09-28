"""Shared data-loading functions used by every page of the dashboard."""

import re
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# allow imports from the src/ folder
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


@st.cache_data
def load_clean_data() -> pd.DataFrame:
    path = ROOT / "data" / "processed" / "weather_clean.parquet"
    if not path.exists():
        st.error(
            "Processed data not found. Run this first:\n\n"
            "```\npython src/data_processing.py\n```"
        )
        st.stop()
    df = pd.read_parquet(path)
    return df


@st.cache_data
def load_daily_agg() -> pd.DataFrame:
    path = ROOT / "data" / "processed" / "weather_daily_agg.parquet"
    if not path.exists():
        st.error("Daily aggregates not found. Run `python src/data_processing.py` first.")
        st.stop()
    df = pd.read_parquet(path)
    return df


@st.cache_data
def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    """Most recent measurement per city - used for the map view."""
    idx = df.groupby("location_name")["last_updated"].idxmax()
    return df.loc[idx].reset_index(drop=True)


def aqi_color(epa_index: float) -> str:
    """Marker color on the map based on the US EPA air-quality index."""
    mapping = {
        1: "#2ecc71",  # good - green
        2: "#f1c40f",  # moderate - yellow
        3: "#e67e22",  # unhealthy for sensitive groups - orange
        4: "#e74c3c",  # unhealthy - red
        5: "#8e44ad",  # very unhealthy - purple
        6: "#7f1d1d",  # hazardous - dark red
    }
    idx = int(round(epa_index)) if pd.notna(epa_index) else 2
    return mapping.get(idx, "#95a5a6")


# Matches a string that contains ONLY: Latin letters (incl. accented), digits,
# spaces and a small set of common punctuation used in place names
# (- . , ' ). Anything outside this range (Chinese/Arabic/Cyrillic/etc. script,
# or a stray backtick) makes the match fail.
_LATIN_ONLY_RE = re.compile(r"^[A-Za-zÀ-ÖØ-öø-ÿ0-9\s\-.,'()]+$")


def is_latin_name(text) -> bool:
    """True if `text` is written using only Latin-script characters."""
    if pd.isna(text):
        return False
    return bool(_LATIN_ONLY_RE.match(str(text)))


def has_apostrophe(text) -> bool:
    """True if `text` contains an apostrophe (' or the backtick variant `)."""
    if pd.isna(text):
        return False
    return ("'" in str(text)) or ("`" in str(text))
