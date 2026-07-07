import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_FILE = "HHS_Unaccompanied_Alien_Children_Program.csv"


def find_data_file() -> Path:
    """Locate the dataset from common project paths."""
    candidates = [
        Path(DATA_FILE),
        Path.cwd() / DATA_FILE,
        Path(__file__).resolve().parents[1] / DATA_FILE,
        Path(__file__).resolve().parents[1] / "data" / DATA_FILE,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"Could not find {DATA_FILE}")


@st.cache_data(show_spinner=False)
def load_and_prepare_data() -> pd.DataFrame:
    """Load, clean, and engineer the capacity analysis dataset."""
    csv_path = find_data_file()

    df = pd.read_csv(csv_path)

    df = df.rename(
        columns={
            "Date": "date",
            "Children apprehended and placed in CBP custody*": "children_apprehended_and_placed_in_cbp_custody",
            "Children in CBP custody": "cbp_custody",
            "Children transferred out of CBP custody": "transferred_out_of_cbp_custody",
            "Children in HHS Care": "hhs_care",
            "Children discharged from HHS Care": "discharged_from_hhs_care",
        }
    )

    df = df.dropna(subset=["date"])
    df["date"] = pd.to_datetime(df["date"], format="%B %d, %Y", errors="coerce")
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)

    # Normalize missing numeric values so totals are calculated cleanly.
    df = df.replace("None", pd.NA)
    numeric_columns = [
        "children_apprehended_and_placed_in_cbp_custody",
        "cbp_custody",
        "transferred_out_of_cbp_custody",
        "hhs_care",
        "discharged_from_hhs_care",
    ]
    for column in numeric_columns:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0)

    df["total_system_load"] = df["cbp_custody"] + df["hhs_care"]
    df["net_daily_intake"] = df["transferred_out_of_cbp_custody"] - df["discharged_from_hhs_care"]
    df["care_load_growth_rate"] = df["total_system_load"].pct_change() * 100
    df["backlog_indicator"] = df["net_daily_intake"].rolling(window=7, min_periods=1).sum()

    return df


def aggregate_for_view(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """Aggregate the data to either daily or weekly intervals."""
    if granularity == "Weekly":
        return (
            df.set_index("date")
            .resample("W-MON")
            .agg(
                {
                    "cbp_custody": "mean",
                    "hhs_care": "mean",
                    "transferred_out_of_cbp_custody": "mean",
                    "discharged_from_hhs_care": "mean",
                    "total_system_load": "mean",
                    "net_daily_intake": "mean",
                    "backlog_indicator": "mean",
                }
            )
            .reset_index()
        )

    return df.copy()


def get_anomaly_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows where operational rules appear to be violated."""
    anomaly_df = df[
        (df["transferred_out_of_cbp_custody"] > df["cbp_custody"])
        | (df["discharged_from_hhs_care"] > df["hhs_care"])
    ].copy()

    if anomaly_df.empty:
        return anomaly_df

    anomaly_df = anomaly_df[["date", "cbp_custody", "transferred_out_of_cbp_custody", "hhs_care", "discharged_from_hhs_care"]].copy()
    anomaly_df["cbp_transfer_excess"] = (
        anomaly_df["transferred_out_of_cbp_custody"] - anomaly_df["cbp_custody"]
    )
    anomaly_df["hhs_discharge_excess"] = (
        anomaly_df["discharged_from_hhs_care"] - anomaly_df["hhs_care"]
    )
    return anomaly_df.reset_index(drop=True)


def prepare_download_csv(df: pd.DataFrame) -> str:
    """Convert DataFrame to CSV string for downloads."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue()


def build_kpi_cards(df: pd.DataFrame) -> None:
    """Render KPI summary cards in a polished executive dashboard style."""
    valid_rows = df.loc[df["total_system_load"].notna()]
    if not valid_rows.empty:
        latest = valid_rows.iloc[-1]
    else:
        latest = df.iloc[-1]

    total_children_under_care = round(float(latest["total_system_load"] if pd.notna(latest["total_system_load"]) else 0), 1)
    net_intake_pressure = round(float(latest["net_daily_intake"] if pd.notna(latest["net_daily_intake"]) else 0), 1)
    backlog_rate = round(float(latest["backlog_indicator"] if pd.notna(latest["backlog_indicator"]) else 0), 1)

    cards = [
        ("Total Children Under Care", f"{total_children_under_care:,}", "Latest system load"),
        ("Net Intake Pressure", f"{net_intake_pressure:+,.1f}", "Transfers minus discharges"),
        ("Backlog Accumulation Rate", f"{backlog_rate:+,.1f}", "7-day rolling intake balance"),
    ]

    cols = st.columns(3)
    for col, (title, value, subtitle) in zip(cols, cards):
        with col:
            st.markdown(
                f"""
                <div style="background: linear-gradient(135deg, #0f172a, #1e3a8a); padding: 18px 20px; border-radius: 16px; margin-bottom: 16px; box-shadow: 0 6px 18px rgba(0,0,0,0.15);">
                    <div style="font-size: 0.9rem; color: #cbd5e1; margin-bottom: 6px;">{title}</div>
                    <div style="font-size: 1.8rem; font-weight: 700; color: white;">{value}</div>
                    <div style="font-size: 0.85rem; color: #bfdbfe; margin-top: 6px;">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def apply_theme(theme: str) -> None:
    """Apply a custom light or dark theme to the Streamlit dashboard."""
    if theme == "Dark":
        st.markdown(
            """
            <style>
                .reportview-container, .main, .block-container {
                    background: #0b1220;
                    color: #e2e8f0;
                }
                .stButton>button {
                    background-color: #1f2937;
                    color: #f8fafc;
                }
                .css-1d391kg, .css-10trblm, .css-ffhzg2 {
                    background-color: #111827;
                    color: #e2e8f0;
                }
                .stMarkdown p, .stText, .stCaption {
                    color: #cbd5e1;
                }
                .stDataFrame>div>div {
                    background-color: #0f172a;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """
            <style>
                .reportview-container, .main, .block-container {
                    background: #f8fafc;
                    color: #0f172a;
                }
                .stButton>button {
                    background-color: #2563eb;
                    color: white;
                }
                .stDataFrame>div>div {
                    background-color: white;
                }
            </style>
            """,
            unsafe_allow_html=True,
        )


st.set_page_config(page_title="Capacity Analysis Dashboard", layout="wide")
st.title("Unaccompanied Children Capacity Dashboard")
st.caption("Executive view of CBP and HHS care capacity, intake pressure, and backlog accumulation.")

with st.sidebar:
    st.header("Filters")
    df = load_and_prepare_data()
    min_date = df["date"].min().date()
    max_date = df["date"].max().date()

    selected_range = st.date_input(
        "Select date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start_date, end_date = selected_range
    else:
        start_date = end_date = selected_range

    granularity = st.radio("View granularity", ["Daily", "Weekly"], horizontal=True)
    theme_choice = st.radio("Theme", ["Light", "Dark"], horizontal=True)
    st.caption("Daily shows the raw cadence; Weekly smooths the series for higher-level reporting.")
    apply_theme(theme_choice)
    st.markdown("---")
    st.subheader("Export")
    st.write("Download the filtered dataset or anomaly report for external review.")

filtered_df = df[(df["date"] >= pd.Timestamp(start_date)) & (df["date"] <= pd.Timestamp(end_date))].copy()
view_df = aggregate_for_view(filtered_df, granularity)

csv_download = prepare_download_csv(filtered_df)
st.download_button(
    "Download filtered dataset",
    data=csv_download,
    file_name="filtered_capacity_data.csv",
    mime="text/csv",
)

build_kpi_cards(view_df)

st.markdown("---")
st.subheader("Operational Anomalies")
st.caption("Rows that indicate potential reporting lag or data-quality concerns in the selected period.")
anomaly_df = get_anomaly_table(filtered_df)
if anomaly_df.empty:
    st.success("No operational anomalies were detected in the selected date range.")
else:
    st.warning(f"Detected {len(anomaly_df)} rows with potential reporting anomalies.")
    top_anomalies = anomaly_df.sort_values(
        by=["cbp_transfer_excess", "hhs_discharge_excess"],
        ascending=False,
    ).head(5)
    st.markdown("**Most severe anomaly days**")
    st.dataframe(top_anomalies, width='stretch', hide_index=True)
    anomaly_csv = prepare_download_csv(anomaly_df)
    st.download_button(
        "Download anomaly report",
        data=anomaly_csv,
        file_name="capacity_anomalies.csv",
        mime="text/csv",
    )

st.markdown("---")
st.subheader("System Load Overview")
st.caption("CBP custody versus HHS care load over time.")
load_chart = view_df[["cbp_custody", "hhs_care"]].copy()
load_chart.index = view_df["date"]
st.line_chart(load_chart, color=["#2563eb", "#f59e0b"], height=320)

st.subheader("Net Intake and Backlog Trends")
st.caption("Positive values indicate net pressure entering the system; negative values suggest temporary relief.")
stress_chart = view_df[["net_daily_intake", "backlog_indicator"]].copy()
stress_chart.index = view_df["date"]
st.line_chart(stress_chart, color=["#dc2626", "#0f766e"], height=320)
