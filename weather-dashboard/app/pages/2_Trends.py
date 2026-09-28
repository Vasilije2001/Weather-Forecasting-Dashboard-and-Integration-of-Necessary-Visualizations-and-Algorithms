"""Time-series trends for weather and environmental indicators."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import streamlit as st
import plotly.express as px
import pandas as pd

from data_loader import load_daily_agg
from analysis import trend_for_city, linear_trend_slope

st.set_page_config(page_title="Trends", page_icon="📈", layout="wide")
st.title("📈 Trends Over Time")

daily = load_daily_agg()

cities = sorted(daily["location_name"].unique())
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    selected_cities = st.multiselect("Cities:", cities, default=cities[:3])
with col2:
    metric = st.selectbox(
        "Metric:",
        ["temperature_celsius", "humidity", "aqi_pm2_5", "aqi_us_epa_index", "wind_kph", "precip_mm"],
        format_func=lambda x: {
            "temperature_celsius": "Temperature (°C)",
            "humidity": "Humidity (%)",
            "aqi_pm2_5": "PM2.5",
            "aqi_us_epa_index": "AQI (US EPA index)",
            "wind_kph": "Wind (km/h)",
            "precip_mm": "Precipitation (mm)",
        }[x],
    )
with col3:
    smoothing = st.slider("Smoothing (days, rolling average):", 1, 30, 7)

date_range = st.slider(
    "Period:",
    min_value=daily["date"].min().to_pydatetime(),
    max_value=daily["date"].max().to_pydatetime(),
    value=(daily["date"].min().to_pydatetime(), daily["date"].max().to_pydatetime()),
)

if not selected_cities:
    st.warning("Select at least one city.")
    st.stop()

frames = []
for city in selected_cities:
    t = trend_for_city(daily, city, metric=metric, window=smoothing)
    t = t[(t["date"] >= date_range[0]) & (t["date"] <= date_range[1])]
    frames.append(t)
plot_df = pd.concat(frames)

fig = px.line(
    plot_df, x="date", y=f"{metric}_smoothed", color="location_name",
    labels={"date": "Date", f"{metric}_smoothed": "Value (smoothed)", "location_name": "City"},
    title=f"Trend: {metric} ({smoothing}-day rolling average)",
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Linear trend slope by city")
st.caption(
    "A positive value means the indicator is rising on average over the period; "
    "negative means it's falling."
)
slopes = {city: linear_trend_slope(daily, city, metric=metric) for city in selected_cities}
slope_df = pd.DataFrame({"City": slopes.keys(), "Trend slope / day": slopes.values()})
st.dataframe(slope_df.sort_values("Trend slope / day", ascending=False), use_container_width=True)
