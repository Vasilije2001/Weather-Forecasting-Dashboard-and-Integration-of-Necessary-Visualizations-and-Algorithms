"""
Home page of the dashboard.

Run (from the project root folder):
    streamlit run app/main.py
"""

import streamlit as st
import plotly.express as px
from data_loader import load_clean_data, latest_snapshot

st.set_page_config(
    page_title="Weather & Environmental Dashboard",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 Interactive Dashboard for Weather and Environmental Data Analysis")
st.caption(
    "Weather and air quality analysis for "
    "cities worldwide, 2024 to present."
)

df = load_clean_data()
snapshot = latest_snapshot(df)

# --- KPI cards ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Cities", snapshot["location_name"].nunique())
col2.metric("Countries", snapshot["country"].nunique())
col3.metric("Total measurements", f"{len(df):,}")
col4.metric(
    "Period",
    f"{df['last_updated'].min().date()} → {df['last_updated'].max().date()}",
)

st.divider()

st.subheader("Current conditions by city (latest measurement)")

c1, c2 = st.columns(2)
with c1:
    fig_temp = px.bar(
        snapshot.sort_values("temperature_celsius", ascending=False),
        x="location_name", y="temperature_celsius",
        color="temperature_celsius", color_continuous_scale="RdBu_r",
        labels={"location_name": "City", "temperature_celsius": "Temperature (°C)"},
        title="Temperature by city",
    )
    st.plotly_chart(fig_temp, use_container_width=True)

with c2:
    fig_aqi = px.bar(
        snapshot.sort_values("aqi_pm2_5", ascending=False),
        x="location_name", y="aqi_pm2_5",
        color="aqi_pm2_5", color_continuous_scale="Oranges",
        labels={"location_name": "City", "aqi_pm2_5": "PM2.5 (µg/m³)"},
        title="Air quality (PM2.5) by city",
    )
    st.plotly_chart(fig_aqi, use_container_width=True)

st.info(
    "👈 Use the side menu (Pages) for: **Interactive Map**, "
    "**Trends over time**, **Air quality analysis**, and "
    "**City clustering by climate profile**."
)

with st.expander("About this dataset"):
    st.write(
        "The dataset contains weather and environmental data (temperature, "
        "humidity, wind, pressure, air quality - PM2.5, PM10, O3, NO2, SO2, CO) "
        "for major cities worldwide, collected at a daily granularity since 2024."
    )
    st.dataframe(df.head(20))
