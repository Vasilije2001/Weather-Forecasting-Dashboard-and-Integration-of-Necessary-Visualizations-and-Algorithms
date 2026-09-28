"""Interactive map - clicking a city shows a detail panel below the map."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.express as px
import pandas as pd

from data_loader import (
    load_clean_data, load_daily_agg, latest_snapshot, aqi_color,
    is_latin_name, has_apostrophe,
)


def _safe_for_js_template(text) -> str:
    """Folium embeds tooltip/popup text inside a JS template literal (backtick
    string) and properly escapes quotes/apostrophes, but does NOT escape a raw
    backtick character or a ${ sequence. Some cities in the dataset (e.g. the
    capital of Tonga) have a ` in their name instead of an apostrophe due to a
    data-entry error, which otherwise breaks the generated JS and causes
    'SyntaxError: missing ) after argument list' in the streamlit_folium
    component - most noticeable only once ALL countries are shown."""
    return str(text).replace("\\", "\\\\").replace("`", "'").replace("${", "$\\{")


st.set_page_config(page_title="Map", page_icon="🗺️", layout="wide")
st.title("🗺️ Interactive City Map")

df = load_clean_data()
daily = load_daily_agg()
snapshot = latest_snapshot(df)

# --- Controls ---
col_a, col_b = st.columns([1, 1])
with col_a:
    map_metric = st.selectbox(
        "Color markers by:",
        options=["temperature_celsius", "aqi_pm2_5", "humidity", "wind_kph"],
        format_func=lambda x: {
            "temperature_celsius": "Temperature (°C)",
            "aqi_pm2_5": "PM2.5",
            "humidity": "Humidity (%)",
            "wind_kph": "Wind (km/h)",
        }[x],
    )
with col_b:
    countries = ["All countries"] + sorted(snapshot["country"].unique().tolist())
    selected_country = st.selectbox("Filter by country:", countries)

with st.expander("🧪 Data-cleanup filters (testing)"):
    st.caption(
        "These filters are here mainly to test whether excluding certain names "
        "changes what shows up on the map. The apostrophe/backtick rendering bug "
        "itself is already fixed above (see `_safe_for_js_template`), so the map "
        "should show every marker regardless - these are optional extra filters."
    )
    exclude_apostrophe = st.checkbox("Exclude cities with an apostrophe (') in the name", value=False)
    latin_only = st.checkbox("Show only Latin-script names (hide Chinese, Arabic, Cyrillic, etc.)", value=False)

map_df = snapshot if selected_country == "All countries" else snapshot[snapshot["country"] == selected_country]

if exclude_apostrophe:
    mask = ~(
        map_df["location_name"].apply(has_apostrophe)
        | map_df["country"].apply(has_apostrophe)
    )
    map_df = map_df[mask]

if latin_only:
    mask = (
        map_df["location_name"].apply(is_latin_name)
        & map_df["country"].apply(is_latin_name)
    )
    map_df = map_df[mask]

# Rows with no coordinates or no value for the chosen metric can't be plotted -
# drop them BEFORE drawing, instead of crashing mid-loop.
rows_before = len(map_df)
map_df = map_df.dropna(subset=["latitude", "longitude", map_metric])
skipped = rows_before - len(map_df)

st.caption(f"🔎 Cities shown on the map: **{len(map_df)}** (out of {rows_before} matching the current filters)")

# --- Map ---
map_data = None
if map_df.empty:
    st.warning("No data to display with the current filters.")
else:
    try:
        m = folium.Map(location=[20, 10], zoom_start=2, tiles="CartoDB positron")
        vmin, vmax = map_df[map_metric].min(), map_df[map_metric].max()

        for _, row in map_df.iterrows():
            try:
                if map_metric == "aqi_pm2_5":
                    color = aqi_color(row["aqi_us_epa_index"])
                else:
                    ratio = 0 if vmax == vmin else (row[map_metric] - vmin) / (vmax - vmin)
                    ratio = min(max(ratio, 0), 1)
                    r = int(255 * ratio)
                    b = int(255 * (1 - ratio))
                    color = f"#{r:02x}44{b:02x}"

                # Plain-text folium.Tooltip (no hand-built HTML, which used to cause
                # issues for certain city/country names). The name still goes through
                # _safe_for_js_template because folium does not escape a raw backtick
                # character when it builds the tooltip JS (see note above).
                safe_name = _safe_for_js_template(row["location_name"])
                safe_country = _safe_for_js_template(row["country"])
                tooltip_text = (
                    f"{safe_name}, {safe_country} | "
                    f"Temp: {row['temperature_celsius']}°C | "
                    f"PM2.5: {row['aqi_pm2_5']:.1f} | "
                    f"Humidity: {row['humidity']}%"
                )

                folium.CircleMarker(
                    location=[float(row["latitude"]), float(row["longitude"])],
                    radius=9,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.85,
                    weight=1,
                    tooltip=folium.Tooltip(tooltip_text),
                    popup=folium.Popup(safe_name, max_width=200),
                ).add_to(m)
            except (ValueError, TypeError):
                skipped += 1
                continue

        if skipped > 0:
            st.caption(f"⚠️ Skipped {skipped} cities due to missing/invalid data.")

        st.caption("Click a city on the map to see a detailed breakdown below.")
        map_data = st_folium(m, width=1200, height=520, returned_objects=["last_object_clicked_tooltip"])

    except Exception as e:
        # If anything breaks while building/rendering the map, SHOW the error
        # instead of leaving the page blank with no clue why.
        st.error("An error occurred while rendering the map:")
        st.exception(e)
        map_data = None

st.divider()

# --- Click detection and detail panel ---
clicked_city = None
if map_data and map_data.get("last_object_clicked_tooltip"):
    tooltip_text = map_data["last_object_clicked_tooltip"]
    # tooltip format: "City, Country | Temp: ... | PM2.5: ... | Humidity: ..."
    for _, row in map_df.iterrows():
        expected_prefix = f"{_safe_for_js_template(row['location_name'])}, {_safe_for_js_template(row['country'])}"
        if tooltip_text.startswith(expected_prefix):
            clicked_city = row["location_name"]
            break

if clicked_city is None:
    st.info("👆 Click a point on the map to see a detailed analysis for that city.")
else:
    city_row = snapshot[snapshot["location_name"] == clicked_city].iloc[0]
    st.subheader(f"📍 {clicked_city}, {city_row['country']}")

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Temperature", f"{city_row['temperature_celsius']:.1f} °C")
    k2.metric("Feels like", f"{city_row['feels_like_celsius']:.1f} °C")
    k3.metric("Humidity", f"{city_row['humidity']:.0f} %")
    k4.metric("Wind", f"{city_row['wind_kph']:.1f} km/h")
    k5.metric("PM2.5", f"{city_row['aqi_pm2_5']:.1f} µg/m³", city_row["aqi_category"])

    city_daily = daily[daily["location_name"] == clicked_city].sort_values("date")

    tab1, tab2 = st.tabs(["Temperature over time", "Air quality over time"])
    with tab1:
        fig = px.line(
            city_daily, x="date", y="temperature_celsius",
            title=f"Daily average temperature - {clicked_city}",
            labels={"date": "Date", "temperature_celsius": "Temperature (°C)"},
        )
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        fig2 = px.line(
            city_daily, x="date", y=["aqi_pm2_5", "aqi_pm10"],
            title=f"PM2.5 / PM10 over time - {clicked_city}",
            labels={"date": "Date", "value": "µg/m³", "variable": "Pollutant"},
        )
        st.plotly_chart(fig2, use_container_width=True)
