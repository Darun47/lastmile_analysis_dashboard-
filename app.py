# ---------------- FA-2: Delivery Analytics Dashboard ----------------
# Student: Poorvi Tumu
# Course: CRS – Year 2 (Maths for AI-II)
# Assessment: Formative Assessment 2
# --------------------------------------------------------------------

import os
import streamlit as st
import pandas as pd
import numpy as np


st.set_page_config(page_title="Delivery Dashboard – FA2", layout="wide")
st.title("📦 Last-mile Delivery Performance Dashboard (FA-2)")

# ---------- DATA PATH FOR STREAMLIT CLOUD ----------
DATA_PATH = "Last mile Delivery Data.csv"

# IMPORTANT: Check if file exists in repo
if not os.path.exists(DATA_PATH):
    st.error(
        "❌ Dataset not found.\n\n"
        "Make sure you uploaded **'Last mile Delivery Data.csv'** "
        "to the SAME folder as app.py in your GitHub repo."
    )
    st.stop()

# ---------- LOAD DATA ----------
df = pd.read_csv(DATA_PATH)

# ---------- DATA CLEANING ----------
df = df.drop_duplicates()
df.columns = [c.strip() for c in df.columns]

required_cols = [
    "Delivery_Time", "Weather", "Traffic", "Vehicle",
    "Agent_Age", "Agent_Rating", "Area", "Category"
]

for col in required_cols:
    if col not in df.columns:
        df[col] = np.nan

df["Delivery_Time"] = pd.to_numeric(df["Delivery_Time"], errors="coerce")
df["Agent_Rating"] = pd.to_numeric(df["Agent_Rating"], errors="coerce")
df["Agent_Age"] = pd.to_numeric(df["Agent_Age"], errors="coerce")

df = df.dropna(subset=["Delivery_Time"])

for c in ["Weather", "Traffic", "Vehicle", "Area", "Category"]:
    df[c] = df[c].fillna("Unknown").astype(str).str.strip().str.title()

df["Age_Group"] = pd.cut(
    df["Agent_Age"].fillna(-1),
    bins=[-1, 24, 40, 200],
    labels=["<25", "25-40", "40+"],
    include_lowest=True
).astype(str)

mean_dt = df["Delivery_Time"].mean()
std_dt = df["Delivery_Time"].std()
df["Late"] = (df["Delivery_Time"] > (mean_dt + std_dt)).astype(int)

# ---------- SIDEBAR FILTERS ----------
st.sidebar.header("🔎 Filters")

def multi(colname):
    return st.sidebar.multiselect(
        colname,
        sorted(df[colname].unique()),
        default=sorted(df[colname].unique())
    )

weather = multi("Weather")
traffic = multi("Traffic")
vehicle = multi("Vehicle")
area = multi("Area")
category = multi("Category")

filtered = df[
    df["Weather"].isin(weather) &
    df["Traffic"].isin(traffic) &
    df["Vehicle"].isin(vehicle) &
    df["Area"].isin(area) &
    df["Category"].isin(category)
]

# ---------- KPI PANEL ----------
st.subheader("📊 Key Performance Indicators")

c1, c2, c3 = st.columns(3)
c1.metric("Avg Delivery Time (mins)", round(filtered["Delivery_Time"].mean(), 2))
c2.metric("Total Deliveries", len(filtered))
c3.metric("Late Deliveries (%)", f"{round(filtered['Late'].mean() * 100, 2)}%")

st.markdown("---")

# ---------- VISUAL 1: Weather ----------
st.subheader("⛅ Delay Analyzer: Weather")
weather_grp = filtered.groupby("Weather")["Delivery_Time"].mean().reset_index()
st.plotly_chart(px.bar(weather_grp, x="Weather", y="Delivery_Time"), use_container_width=True)

# ---------- VISUAL 1b: Traffic ----------
st.subheader("🚦 Delay Analyzer: Traffic")
traffic_grp = filtered.groupby("Traffic")["Delivery_Time"].mean().reset_index()
st.plotly_chart(px.bar(traffic_grp, x="Traffic", y="Delivery_Time"), use_container_width=True)

st.markdown("---")

# ---------- VISUAL 2: Vehicle ----------
st.subheader("🚚 Vehicle Performance")
vehicle_grp = filtered.groupby("Vehicle")["Delivery_Time"].mean().reset_index()
st.plotly_chart(px.bar(vehicle_grp, x="Vehicle", y="Delivery_Time"), use_container_width=True)

st.markdown("---")

# ---------- VISUAL 3: Agent Scatter ----------
st.subheader("🧍 Agent Performance (Rating vs Time)")
st.plotly_chart(
    px.scatter(filtered, x="Agent_Rating", y="Delivery_Time", color="Age_Group"),
    use_container_width=True
)

st.markdown("---")

# ---------- VISUAL 4: Area ----------
st.subheader("🌍 Regional Bottlenecks (Area)")
area_grp = filtered.groupby("Area")["Delivery_Time"].mean().reset_index()
st.plotly_chart(
    px.bar(area_grp, x="Area", y="Delivery_Time", color="Delivery_Time"),
    use_container_width=True
)

st.markdown("---")

# ---------- VISUAL 5: Category ----------
st.subheader("📦 Category Delivery Distribution")
st.plotly_chart(
    px.box(filtered, x="Category", y="Delivery_Time"),
    use_container_width=True
)

st.caption("Late Delivery = Delivery_Time > mean + 1*std (FA-2 rule).")
