"""Forecast page - project a metric N days into the future for a chosen city."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd

from data_loader import load_daily_agg
from forecasting import forecast_city

st.set_page_config(page_title="Forecast", page_icon="🔮", layout="wide")
st.title("🔮 Forecast")
st.caption(
    "Projects a chosen metric forward in time for a single city, using a "
    "statistical time-series model fitted on historical daily data. This is an "
    "exploratory / methodological demonstration, not a "
    "meteorological forecasting system."
)

daily = load_daily_agg()
cities = sorted(daily["location_name"].unique())

# --- Controls ---
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    city = st.selectbox("City:", cities)
with col2:
    metric = st.selectbox(
        "Metric to forecast:",
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
    method = st.selectbox(
        "Algorithm:",
        ["seasonal_regression", "holt_linear", "linear_regression"],
        format_func=lambda x: {
            "seasonal_regression": "Seasonal regression (trend + yearly Fourier cycle)",
            "holt_linear": "Holt's linear trend (no seasonality)",
            "linear_regression": "Linear regression (naive baseline)",
        }[x],
    )

col4, col5 = st.columns([1, 2])
with col4:
    horizon_days = st.number_input("Forecast horizon (days):", min_value=1, max_value=90, value=7, step=1)

city_daily = daily[daily["location_name"] == city].sort_values("date")
data_min = city_daily["date"].min().to_pydatetime()
data_max = city_daily["date"].max().to_pydatetime()

with col5:
    train_range = st.slider(
        "Training data range (which history the model is fitted on):",
        min_value=data_min, max_value=data_max, value=(data_min, data_max),
    )

st.caption(
    f"Available history for **{city}**: {data_min.date()} → {data_max.date()} "
    f"({(data_max - data_min).days} days). Training window selected: "
    f"{(train_range[1] - train_range[0]).days} days."
)

run = st.button("Run forecast", type="primary")

if run:
    try:
        result = forecast_city(
            daily, city, metric,
            horizon_days=int(horizon_days),
            method=method,
            train_start=pd.Timestamp(train_range[0]),
            train_end=pd.Timestamp(train_range[1]),
        )
    except ValueError as e:
        st.error(str(e))
        st.stop()

    if result.fallback_reason:
        st.warning(f"⚠️ {result.fallback_reason}")

    metric_label = {
        "temperature_celsius": "Temperature (°C)", "humidity": "Humidity (%)",
        "aqi_pm2_5": "PM2.5", "aqi_us_epa_index": "AQI (US EPA index)",
        "wind_kph": "Wind (km/h)", "precip_mm": "Precipitation (mm)",
    }[metric]

    fig = go.Figure()
    # only plot the most recent portion of history so the forecast is visible/readable
    hist_tail = result.history.tail(120)
    fig.add_trace(go.Scatter(
        x=hist_tail["date"], y=hist_tail["value"],
        mode="lines", name="History", line=dict(color="#3498db"),
    ))

    # Draw the forecast line starting from the LAST ACTUAL history point, purely
    # so the two lines visually connect on the chart. The underlying forecast
    # values (used below in the table) are NOT changed - a plain OLS/ETS trend
    # line generally does not pass exactly through the last observed point
    # (it's fitted across the whole training window, not anchored to the most
    # recent value), so without this the forecast line appears to "jump" at
    # the boundary even though both segments are correct.
    last_actual = hist_tail.iloc[-1]
    forecast_plot_x = pd.concat([pd.Series([last_actual["date"]]), result.forecast["date"]], ignore_index=True)
    forecast_plot_y = pd.concat([pd.Series([last_actual["value"]]), result.forecast["value"]], ignore_index=True)
    fig.add_trace(go.Scatter(
        x=forecast_plot_x, y=forecast_plot_y,
        mode="lines+markers", name="Forecast", line=dict(color="#e74c3c"),
    ))
    fig.add_trace(go.Scatter(
        x=pd.concat([result.forecast["date"], result.forecast["date"][::-1]]),
        y=pd.concat([result.forecast["upper"], result.forecast["lower"][::-1]]),
        fill="toself", fillcolor="rgba(231,76,60,0.15)",
        line=dict(color="rgba(255,255,255,0)"), name="~95% band", showlegend=True,
    ))
    fig.update_layout(
        title=f"{metric_label} forecast for {city} - next {horizon_days} days ({result.method_used})",
        xaxis_title="Date", yaxis_title=metric_label,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Note: the forecast line is drawn starting from the last actual data point "
        "so the chart reads continuously. The model's own fitted value at that same "
        "point may differ slightly from the actual reading - see the methodology "
        "notes below for why."
    )

    st.subheader("Forecasted values")
    display_df = result.forecast.copy()
    display_df["date"] = display_df["date"].dt.date
    display_df = display_df.rename(columns={
        "date": "Date", "value": "Forecast", "lower": "Lower bound", "upper": "Upper bound",
    })
    st.dataframe(display_df.round(2), use_container_width=True)

    with st.expander("Methodology notes"):
        st.markdown(
            "- **Seasonal regression** fits a linear trend plus a low-order "
            "Fourier (harmonic) series representing the repeating yearly "
            "cycle, by ordinary least squares. It needs at least ~1.5 years "
            "of daily history to identify a yearly cycle at all, and "
            "automatically falls back to Holt's linear trend if there isn't "
            "enough data in the selected training window. *(An earlier "
            "version of this dashboard used classic Holt-Winters exponential "
            "smoothing here instead. It was replaced after testing showed "
            "the optimizer failed to converge on this dataset - fitting 365 "
            "free seasonal parameters from only ~2 years of data is "
            "underdetermined, and produced day-to-day swings of 3-4°C that "
            "aren't physically plausible. The Fourier approach represents "
            "the same yearly cycle with about 8 parameters instead of 365, "
            "which is far better matched to the amount of data available - "
            "this trade-off is worth describing in the methodology chapter.)*\n"
            "- **Holt's linear trend** models level + trend only (no seasonality) - "
            "a reasonable choice for metrics without a strong annual cycle, or "
            "short training windows.\n"
            "- **Linear regression** fits a single straight line through the "
            "training window and extrapolates it - the simplest possible baseline, "
            "useful for showing how much the other two methods improve on a naive fit.\n"
            "- **Why the forecast line can visually 'jump' at the boundary**: a "
            "trend line (OLS or ETS) is fitted across the *whole* training window, "
            "so its value at the last training day generally does not exactly equal "
            "the last *actual* reading - it represents the underlying trend, not the "
            "most recent noisy observation. Methods that weight recent data more "
            "heavily (Holt's linear trend) stay closer to the last actual value than "
            "plain OLS regression, which weights every point in the window equally. "
            "The chart above starts the forecast line from the last actual point "
            "purely for visual continuity; the table below reports the model's own "
            "(unadjusted) forecast values.\n"
            "- The shaded band is a rough ±1.96×(residual std. dev.) band around the "
            "point forecast, **not** a rigorous statistical prediction interval - "
            "good for visual intuition, should be described as such."
        )
else:
    st.info("👆 Set the options above and click **Run forecast**.")
