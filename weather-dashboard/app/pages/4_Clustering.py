"""City clustering by climate profile (K-Means)."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

import streamlit as st
import plotly.express as px

from data_loader import load_clean_data
from analysis import climate_profile_per_city, cluster_cities, elbow_data

st.set_page_config(page_title="Clustering", page_icon="🔬", layout="wide")
st.title("🔬 City Clustering by Climate Profile")
st.caption(
    "Grouping cities based on average temperature, humidity, wind, precipitation, "
    "UV index and PM2.5 - K-Means method (unsupervised learning)."
)

df = load_clean_data()
profile = climate_profile_per_city(df)

col1, col2 = st.columns([1, 3])
with col1:
    n_clusters = st.slider("Number of clusters (k):", 2, 8, 4)
    show_elbow = st.checkbox("Show elbow plot (choosing optimal k)")

profile_clustered, model, scaler = cluster_cities(profile, n_clusters=n_clusters)
profile_clustered["cluster"] = profile_clustered["cluster"].astype(str)

if show_elbow:
    st.subheader("Elbow method - choosing the optimal number of clusters")
    edf = elbow_data(profile, max_k=10)
    fig_elbow = px.line(edf, x="k", y="inertia", markers=True,
                         labels={"k": "Number of clusters (k)", "inertia": "Inertia (WCSS)"})
    st.plotly_chart(fig_elbow, use_container_width=True)
    st.caption(
        "The 'elbow' in the chart (where the drop in inertia slows down) suggests "
        "a reasonable number of clusters - a standard argument."
    )

st.subheader("Cities on the map, colored by cluster")
fig_map = px.scatter_geo(
    profile_clustered,
    lat="latitude", lon="longitude",
    color="cluster", hover_name="location_name",
    hover_data={"avg_temp": ":.1f", "avg_humidity": ":.0f", "avg_pm2_5": ":.1f",
                "latitude": False, "longitude": False},
    projection="natural earth",
    title=f"K-Means clustering (k={n_clusters})",
)
fig_map.update_traces(marker=dict(size=12))
st.plotly_chart(fig_map, use_container_width=True)

st.subheader("Cluster profile (average values)")
cluster_summary = profile_clustered.groupby("cluster")[
    ["avg_temp", "avg_humidity", "avg_wind", "avg_precip", "avg_pm2_5", "avg_uv"]
].mean().round(2)
st.dataframe(cluster_summary, use_container_width=True)

st.subheader("Detailed city table")
st.dataframe(
    profile_clustered[["country", "location_name", "cluster", "avg_temp",
                        "avg_humidity", "avg_wind", "avg_pm2_5"]].sort_values("cluster"),
    use_container_width=True,
)
