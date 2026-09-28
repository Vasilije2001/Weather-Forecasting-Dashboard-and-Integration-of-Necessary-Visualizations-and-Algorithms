An interactive dashboard for exploring weather and air quality data for cities worldwide. It combines a geographic map, a correlation heatmap, K-Means climate clustering, and time-series forecasting in a single multi-page [Streamlit](https://streamlit.io/) app.

Built as part of a master's thesis on **data visualization**, with the goal of showing that maps, a correlation matrix, clustering, and regression algorithms can be integrated into one coherent, easy-to-read weather dashboard.

## Features

| Page | What it does |
|---|---|
| **Home** | KPI cards (cities, countries, measurements, period) and bar charts of the latest temperature and PM2.5 per city |
| **Map** | Interactive world map (Folium) with city markers colored by a selected metric; click a marker for city details |
| **Trends** | Compare multiple cities on one metric over a selectable period, with an adjustable rolling-average smoothing (1–30 days) and a table of linear trend slopes per city |
| **Air Quality** | Pearson correlation heatmap of 13 weather and air quality variables, plus Isolation Forest anomaly detection on a temperature vs. PM2.5 scatter plot (adjustable expected anomaly rate, 0.5–10 %) |
| **Clustering** | K-Means grouping of cities by climate profile (temperature, humidity, wind, precipitation, PM2.5, UV), with an elbow chart for choosing *k* |
| **Forecast** | Temperature and other metric forecasts with a shaded uncertainty band. Choose between seasonal (Fourier) regression, Holt's linear trend, or plain linear regression |

## Screenshots

<p align="center">
  <img src="screenshots/map.png" width="48%" alt="Interactive world map" />
  <img src="screenshots/correlation.png" width="48%" alt="Correlation heatmap" />
</p>
<p align="center">
  <img src="screenshots/clustering.png" width="48%" alt="K-Means clustering of cities" />
  <img src="screenshots/forecast_seasonal.png" width="48%" alt="Seasonal regression forecast" />
</p>

## Tech stack

- **Python**: pandas, NumPy, PyArrow (Parquet storage)
- **Machine learning / statistics**: scikit-learn (K-Means, Isolation Forest), statsmodels (Holt's linear trend)
- **Visualization / UI**: Streamlit, Plotly, Folium, streamlit-folium

## Project structure

```
weather-dashboard/
├── app/
│   ├── main.py               # Home page (entry point)
│   ├── data_loader.py        # Cached data loading shared by all pages
│   └── pages/
│       ├── 1_Map.py
│       ├── 2_Trends.py
│       ├── 3_Air_Quality.py
│       ├── 4_Clustering.py
│       └── 5_Forecast.py
├── src/
│   ├── data_processing.py    # Cleaning and aggregation pipeline
│   ├── analysis.py           # Correlation, K-Means, Isolation Forest
│   ├── forecasting.py        # Linear, Holt, and seasonal regression
│   └── generate_sample_data.py  # Synthetic data for quick testing
├── data/
│   ├── raw/                  # global_weather.csv goes here
│   └── processed/            # Parquet files produced by data_processing.py
└── requirements.txt
```

The code is split into three layers: data preparation (`src/data_processing.py`), analytics (`src/analysis.py`, `src/forecasting.py`), and presentation (`app/`). The analytics functions take and return plain DataFrames and have no Streamlit dependency.

## Getting started

### 1. Install dependencies

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Developed on Python 3.12; a recent Python 3 version is recommended.

### 2. Get the data

Download the **World Weather Repository** dataset from Kaggle and place the CSV at `data/raw/global_weather.csv`:

<https://www.kaggle.com/datasets/nelgiriyewithana/global-weather-repository>

No Kaggle account handy? You can generate a synthetic dataset with the same schema for testing:

```bash
python src/generate_sample_data.py
```

### 3. Process the data

```bash
python src/data_processing.py
```

This cleans the raw CSV and writes `weather_clean.parquet` and `weather_daily_agg.parquet` to `data/processed/`. The steps are:

1. Drop duplicates
2. Keep metric columns only (drop redundant Fahrenheit/mph versions)
3. Impute missing values with the per-city median
4. Check physical validity (e.g. humidity outside 0–100 % is set to missing)
5. Drop cities with fewer than 180 measurements
6. Aggregate to daily values per city

### 4. Run the dashboard

From the project root:

```bash
streamlit run app/main.py
```

Then open the URL shown in the terminal (usually <http://localhost:8501>).

## How the forecasting works

Three statistical models are available on the Forecast page:

- **Seasonal regression (default)**: linear trend plus 3 Fourier harmonic pairs for the yearly cycle, fitted by least squares. Used when a city has at least ~1.5 years of history.
- **Holt's linear trend**: double exponential smoothing. Automatic fallback when there isn't enough history for the seasonal model.
- **Linear regression**: a straight-line baseline for comparison.

The uncertainty band is `forecast ± 1.96 × std(residuals)`, a simplified indicator rather than a rigorous prediction interval.

## Limitations

- The forecasts are **statistical extrapolations of a single city's history**, not physical weather models. They capture the typical seasonal pattern but cannot predict one-off events such as heat waves.
- Linear regression is sensitive to the length of the history window and behaves poorly on strongly seasonal data. It is included as a baseline.
- The app runs on a static snapshot of the dataset, not on live data.
- The visual design has not been evaluated in a formal user study.

## Data source

Elgiriyewithana, N. *World Weather Repository (Daily Updating)*. Kaggle. <https://www.kaggle.com/datasets/nelgiriyewithana/global-weather-repository>
