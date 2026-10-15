"""Streamlit dashboard: backtest results, error map and the latest day-ahead forecast.

streamlit run app/dashboard.py
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from gasfc.backtest import scores, scores_by_ldz, skill  # noqa: E402
from gasfc.config import LDZ_NAMES, PROCESSED  # noqa: E402
from gasfc.geography import assign_ldz  # noqa: E402

MODEL = "gbm_ng_correction"
MODELS = [
    "seasonal_naive",
    "cwv_regression",
    "gbm_cwv",
    "gbm_pop_weather",
    "gbm_cwv_pop_weather",
    MODEL,
]
LABELS = {
    "ng_forecast_da": "National Gas day-ahead",
    "seasonal_naive": "Same day last week",
    "cwv_regression": "CWV regression",
    "gbm_cwv": "LightGBM + CWV",
    "gbm_pop_weather": "LightGBM + population-weighted weather",
    "gbm_cwv_pop_weather": "LightGBM + CWV + population-weighted weather",
    MODEL: "LightGBM correcting the National Gas forecast",
}

st.set_page_config(page_title="GB gas demand forecast", layout="wide")


@st.cache_data
def load() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    preds = pd.read_parquet(PROCESSED / "backtest_predictions.parquet")
    cells = pd.read_parquet(PROCESSED / "population_cells.parquet")
    cells["ldz"] = assign_ldz(cells)
    lon, lat = Transformer.from_crs(27700, 4326, always_xy=True).transform(
        cells["easting"], cells["northing"]
    )
    cells["lon"], cells["lat"] = lon, lat
    fc_path = PROCESSED / "forecasts.parquet"
    forecasts = pd.read_parquet(fc_path) if fc_path.exists() else None
    return preds, cells, forecasts


preds, cells, forecasts = load()
table = scores(preds, MODELS)
table["skill"] = skill(table)

st.title("GB gas demand: day-ahead forecasts by LDZ")
st.caption(
    f"Rolling-origin backtest, retrained monthly, {preds['gas_day'].min():%b %Y} to "
    f"{preds['gas_day'].max():%d %b %Y}. Weather inputs are forecasts issued the day before."
)

c1, c2, c3 = st.columns(3)
c1.metric("Model MAPE", f"{table.loc[MODEL, 'mape']:.2f}%")
c2.metric("National Gas day-ahead MAPE", f"{table.loc['ng_forecast_da', 'mape']:.2f}%")
c3.metric("Improvement on National Gas", f"{table.loc[MODEL, 'skill']:+.1f}%")

st.subheader("Model comparison")
show = table.rename(index=LABELS)[["mape", "mape_winter", "mape_summer", "mae", "bias", "skill"]]
show.columns = ["MAPE %", "MAPE % (Nov-Mar)", "MAPE % (Apr-Oct)", "MAE mcm/d", "Bias mcm/d", "Skill vs NG %"]
st.dataframe(show.style.format("{:.2f}"), width="stretch")

left, right = st.columns([3, 2])
with left:
    st.subheader("Forecast vs actual")
    ldz = st.selectbox(
        "LDZ",
        sorted(preds["ldz"].unique()),
        format_func=lambda z: f"{z}: {LDZ_NAMES[z]}",
        index=sorted(preds["ldz"].unique()).index("WM"),
    )
    p = preds[preds["ldz"] == ldz].sort_values("gas_day")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=p["gas_day"], y=p["band_p90"], line={"width": 0}, showlegend=False, hoverinfo="skip")
    )
    fig.add_trace(
        go.Scatter(
            x=p["gas_day"],
            y=p["band_p10"],
            fill="tonexty",
            line={"width": 0},
            name="P10-P90",
            fillcolor="rgba(31,119,180,0.18)",
        )
    )
    fig.add_trace(
        go.Scatter(x=p["gas_day"], y=p["demand"], name="Actual", line={"color": "#222", "width": 1.5})
    )
    fig.add_trace(
        go.Scatter(x=p["gas_day"], y=p[MODEL], name="Model", line={"color": "#1f77b4", "width": 1.2})
    )
    fig.add_trace(
        go.Scatter(
            x=p["gas_day"],
            y=p["ng_forecast_da"],
            name="National Gas",
            line={"color": "#ff7f0e", "width": 1, "dash": "dot"},
        )
    )
    fig.update_layout(
        height=420,
        yaxis_title="Demand (mcm/day)",
        margin={"t": 10, "b": 10},
        legend={"orientation": "h", "y": 1.08},
    )
    st.plotly_chart(fig, width="stretch")

with right:
    st.subheader("Error by LDZ")
    by_ldz = scores_by_ldz(preds, [MODEL])
    by_ldz["improvement"] = (1 - by_ldz[MODEL] / by_ldz["ng_forecast_da"]) * 100
    metric = st.radio("Colour by", ["Model MAPE %", "Improvement on National Gas %"], horizontal=True)
    col = MODEL if metric.startswith("Model") else "improvement"
    m = cells.merge(by_ldz[[col]].rename(columns={col: "value"}), left_on="ldz", right_index=True)
    fig = px.scatter_map(
        m,
        lat="lat",
        lon="lon",
        color="value",
        size="population",
        size_max=9,
        hover_data={"ldz": True, "value": ":.2f", "population": ":,.0f", "lat": False, "lon": False},
        color_continuous_scale="RdYlGn_r" if col == MODEL else "RdYlGn",
        zoom=4.4,
        center={"lat": 54.4, "lon": -2.6},
        map_style="carto-positron",
        height=470,
    )
    fig.update_layout(margin={"t": 0, "b": 0, "l": 0, "r": 0}, coloraxis_colorbar={"title": ""})
    st.plotly_chart(fig, width="stretch")
    st.caption(
        "Points are 5 km census population cells, sized by population and coloured by their LDZ's error."
    )

st.subheader("Monthly error")
mp = preds.dropna(subset=["demand", "ng_forecast_da", MODEL]).copy()
mp["month"] = mp["gas_day"].dt.to_period("M").dt.to_timestamp()
monthly = (
    pd.DataFrame(
        {
            LABELS["ng_forecast_da"]: (mp["ng_forecast_da"] - mp["demand"])
            .abs()
            .div(mp["demand"])
            .groupby(mp["month"])
            .mean()
            * 100,
            "Model": (mp[MODEL] - mp["demand"]).abs().div(mp["demand"]).groupby(mp["month"]).mean() * 100,
        }
    )
    .reset_index()
    .melt(id_vars="month", var_name="forecast", value_name="MAPE %")
)
fig = px.bar(
    monthly,
    x="month",
    y="MAPE %",
    color="forecast",
    barmode="group",
    height=320,
    color_discrete_sequence=["#ff7f0e", "#1f77b4"],
)
fig.update_layout(
    margin={"t": 10, "b": 10}, legend={"orientation": "h", "y": 1.1, "title": ""}, xaxis_title=""
)
st.plotly_chart(fig, width="stretch")

if forecasts is not None and not forecasts.empty:
    st.subheader("Latest day-ahead forecast")
    latest = forecasts[forecasts["issued_at"] == forecasts["issued_at"].max()].copy()
    latest["LDZ"] = latest["ldz"].map(lambda z: f"{z}: {LDZ_NAMES[z]}")
    st.caption(
        f"Gas day {latest['gas_day'].iloc[0]:%A %d %B %Y}, issued {latest['issued_at'].iloc[0]:%d %b %H:%M}"
    )
    st.dataframe(
        latest[["LDZ", "forecast", "p10", "p90"]].set_index("LDZ").style.format("{:.2f}"), width="stretch"
    )
