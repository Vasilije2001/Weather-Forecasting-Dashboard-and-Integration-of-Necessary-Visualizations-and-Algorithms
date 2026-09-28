"""Air quality analysis and correlation with weather factors."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import streamlit as st
import plotly.express as px

from data_loader import load_clean_data
from analysis import correlation_matrix, detect_anomalies

st.set_page_config(page_title="Air Quality", page_icon="🌫️", layout="wide")
st.title("🌫️ Air Quality - Correlations and Anomalies")

df = load_clean_data()

st.subheader("Correlation matrix: weather ↔ air quality")
corr = correlation_matrix(df)
fig_corr = px.imshow(
    corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
    aspect="auto", title="Pearson correlation",
)
st.plotly_chart(fig_corr, use_container_width=True)
st.caption(
    "Values close to 1 or -1 indicate a strong (positive/negative) relationship. "
    "For example, a negative correlation between wind speed and PM2.5 concentration "
    "is expected (wind disperses pollution)."
)

st.divider()

st.subheader("Relationship between two variables (scatter)")
c1, c2 = st.columns(2)
numeric_cols = df.select_dtypes("number").columns.tolist()
with c1:
    x_var = st.selectbox("X axis:", numeric_cols, index=numeric_cols.index("humidity") if "humidity" in numeric_cols else 0)
with c2:
    y_var = st.selectbox("Y axis:", numeric_cols, index=numeric_cols.index("aqi_pm2_5") if "aqi_pm2_5" in numeric_cols else 1)

fig_scatter = px.scatter(
    df.sample(min(3000, len(df))), x=x_var, y=y_var, color="country",
    opacity=0.6, trendline="ols",
    title=f"{y_var} vs {x_var}",
)
st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

st.subheader("Anomaly detection (Isolation Forest)")
st.caption("Automatic detection of unusual weather/AQI value combinations (e.g. extreme PM2.5 spikes).")

contamination = st.slider("Expected anomaly rate (%)", 0.5, 10.0, 2.0) / 100
df_anom = detect_anomalies(df, contamination=contamination)
anomalies = df_anom[df_anom["is_anomaly"] == 1]

st.write(f"Found **{len(anomalies)}** anomalies out of {len(df_anom):,} records.")

fig_anom = px.scatter(
    df_anom.sample(min(4000, len(df_anom))),
    x="temperature_celsius", y="aqi_pm2_5", color="is_anomaly",
    color_discrete_map={0: "#3498db", 1: "#e74c3c"},
    labels={"is_anomaly": "Anomaly"},
    title="Temperature vs PM2.5 (red = anomaly)",
)
st.plotly_chart(fig_anom, use_container_width=True)

st.dataframe(
    anomalies[["country", "location_name", "last_updated", "temperature_celsius",
               "humidity", "wind_kph", "aqi_pm2_5", "aqi_pm10"]].sort_values("last_updated", ascending=False),
    use_container_width=True,
)
