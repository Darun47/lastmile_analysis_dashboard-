# Debuggable FA-2 Streamlit app (improved)
# Paste into app.py and run. This adds diagnostics to show why graphs may be empty.

import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Delivery Dashboard – FA2 (debug)", layout="wide")
st.title("📦 Last-mile Delivery Dashboard — Debug Friendly")

# ---- DATA PATH ----
DATA_PATH = "Last mile Delivery Data.csv"
if not os.path.exists(DATA_PATH):
    st.error(f"Dataset not found: {DATA_PATH}. Upload CSV to repo root.")
    st.stop()

# ---- LOAD ----
df_raw = pd.read_csv(DATA_PATH, dtype=str)  # read as strings first to inspect
st.sidebar.markdown("*Data preview & diagnostics*")

# ---- Normalize column names and trim whitespace in headers & values ----
df_raw.columns = [c.strip() for c in df_raw.columns]
df = df_raw.copy()
for c in df.columns:
    # trim string values and replace empty strings with NaN
    try:
        df[c] = df[c].astype(str).str.strip().replace({"": np.nan, "nan": np.nan, "None": np.nan})
    except Exception:
        pass

# ---- attempt to map common column name variants to required names ----
# common variants to look for
variants = {
    "Delivery_Time": ["Delivery_Time", "Delivery Time", "delivery_time", "delivery time", "TimeTaken", "Time Taken"],
    "Weather": ["Weather", "weather", "WEATHER"],
    "Traffic": ["Traffic", "traffic", "Traffic Level", "Traffic_Level"],
    "Vehicle": ["Vehicle", "vehicle", "Vehicle Type", "Vehicle_Type"],
    "Agent_Age": ["Agent_Age", "Agent Age", "Age", "agent_age"],
    "Agent_Rating": ["Agent_Rating", "Agent Rating", "Rating", "agent_rating"],
    "Area": ["Area", "area", "Delivery Area", "Location"],
    "Category": ["Category", "category", "Product Category"]
}

col_map = {}
available_cols = set(df.columns.tolist())

for target, variant_list in variants.items():
    found = None
    for v in variant_list:
        if v in available_cols:
            found = v
            break
        # try case-insensitive match
        for ac in available_cols:
            if ac.lower() == v.lower():
                found = ac
                break
        if found:
            break
    if found:
        col_map[target] = found
    else:
        col_map[target] = None

# Show mapping diagnostics
st.sidebar.write("*Column mapping (target → file column)*")
for k, v in col_map.items():
    st.sidebar.write(f"- {k}  →  {v}")

# If essential Delivery_Time not found, stop with clear message
if col_map["Delivery_Time"] is None:
    st.error("Could not find a column that contains delivery time. Check your CSV header names. Possible names: 'Delivery_Time' or 'Delivery Time'.")
    st.stop()

# ---- Create working df with standard column names ----
work = pd.DataFrame()
for target in variants.keys():
    src = col_map.get(target)
    if src:
        work[target] = df[src]
    else:
        work[target] = np.nan

# ---- Convert numeric columns safely ----
for col in ["Delivery_Time", "Agent_Rating", "Agent_Age"]:
    if col in work.columns:
        work[col] = pd.to_numeric(work[col], errors="coerce")

# Drop rows missing Delivery_Time (essential)
before_rows = len(work)
work = work.dropna(subset=["Delivery_Time"])
after_rows = len(work)

st.sidebar.write(f"Rows before dropping missing Delivery_Time: {before_rows}")
st.sidebar.write(f"Rows after dropping missing Delivery_Time: {after_rows}")

# Quick data preview and column list
st.sidebar.markdown("### Data preview (first 5 rows)")
st.sidebar.dataframe(work.head())

st.markdown("### Quick diagnostics")
st.write("*Columns detected in file:*", list(df.columns))
st.write("*Standardized columns used in analysis:*", list(work.columns))
st.write(f"Rows available for analysis: {len(work)}")

# Show value counts for the main categorical columns (helps spot weird values)
with st.expander("Value counts (quick)"):
    for cat in ["Weather", "Traffic", "Vehicle", "Area", "Category"]:
        if cat in work.columns:
            st.write(f"{cat}")
            st.write(work[cat].value_counts(dropna=False).head(20))

# ---- If after cleaning there are zero rows, stop with guidance ----
if work.empty:
    st.error("After cleaning, there are 0 rows. Likely causes:\n"
             "• Delivery_Time column is empty or non-numeric everywhere.\n"
             "• Your CSV has header mismatches. Check header names and sample values shown in sidebar.")
    st.stop()

# ---- Create Age_Group, Late flag ----
work["Age_Group"] = pd.cut(work["Agent_Age"].fillna(-1), bins=[-1,24,40,200], labels=["<25","25-40","40+"], include_lowest=True).astype(str).replace("nan","Unknown")
mean_dt = work["Delivery_Time"].mean()
std_dt = work["Delivery_Time"].std()
threshold = mean_dt + std_dt
work["Late"] = (work["Delivery_Time"] > threshold).astype(int)

# ---- Sidebar filters (use unique values from work) ----
st.sidebar.markdown("---")
st.sidebar.header("Filters (if graphs blank, check these)")

def safe_multiselect(label, col):
    vals = sorted(work[col].dropna().unique().tolist())
    if not vals:
        return []
    return st.sidebar.multiselect(label, vals, default=vals)

weather_sel = safe_multiselect("Weather", "Weather")
traffic_sel = safe_multiselect("Traffic", "Traffic")
vehicle_sel = safe_multiselect("Vehicle", "Vehicle")
area_sel = safe_multiselect("Area", "Area")
category_sel = safe_multiselect("Category", "Category")

filtered = work.copy()
if weather_sel:
    filtered = filtered[filtered["Weather"].isin(weather_sel)]
if traffic_sel:
    filtered = filtered[filtered["Traffic"].isin(traffic_sel)]
if vehicle_sel:
    filtered = filtered[filtered["Vehicle"].isin(vehicle_sel)]
if area_sel:
    filtered = filtered[filtered["Area"].isin(area_sel)]
if category_sel:
    filtered = filtered[filtered["Category"].isin(category_sel)]

st.write(f"Rows after applying filters: {len(filtered)}")

if filtered.empty:
    st.warning("No rows match selected filters. Possible actions:\n"
               "• Clear some filters in the sidebar (click to unselect),\n"
               "• Check value counts in the diagnostics (sidebar) to choose valid options,\n"
               "• Or click the button below to reset filters.")
    if st.button("Reset filters"):
        # simple page refresh workaround
        st.experimental_rerun()

# ---- KPIs ----
st.subheader("Key metrics")
col1, col2, col3 = st.columns(3)
col1.metric("Avg Delivery Time (mins)", round(filtered["Delivery_Time"].mean(),2) if not filtered.empty else "—")
col2.metric("Total Deliveries", len(filtered))
col3.metric("Late Deliveries (%)", f"{round(filtered['Late'].mean()*100,2) if len(filtered)>0 else 0}%")

st.markdown("---")

# ---- PLOTTING (always check for empty data before plotting) ----
def safe_bar(df_plot, x, y, title):
    if df_plot.empty:
        st.info(f"No data to plot for {title}.")
        return
    fig = px.bar(df_plot, x=x, y=y, title=title)
    st.plotly_chart(fig, use_container_width=True)

def safe_scatter(df_plot, x, y, color, title):
    if df_plot.empty:
        st.info(f"No data to plot for {title}.")
        return
    fig = px.scatter(df_plot, x=x, y=y, color=color, title=title)
    st.plotly_chart(fig, use_container_width=True)

# Visual 1: Weather
st.subheader("Delay Analyzer — Weather")
weather_grp = filtered.groupby("Weather", as_index=False)["Delivery_Time"].mean().sort_values("Delivery_Time", ascending=False)
safe_bar(weather_grp, "Weather", "Delivery_Time", "Avg Delivery Time by Weather")

# Visual 1b: Traffic
st.subheader("Delay Analyzer — Traffic")
traffic_grp = filtered.groupby("Traffic", as_index=False)["Delivery_Time"].mean().sort_values("Delivery_Time", ascending=False)
safe_bar(traffic_grp, "Traffic", "Delivery_Time", "Avg Delivery Time by Traffic")

# Visual 2: Vehicle
st.subheader("Vehicle Performance")
vehicle_grp = filtered.groupby("Vehicle", as_index=False)["Delivery_Time"].mean().sort_values("Delivery_Time")
safe_bar(vehicle_grp, "Vehicle", "Delivery_Time", "Avg Delivery Time by Vehicle")

# Visual 3: Agent Performance
st.subheader("Agent Rating vs Delivery Time")
safe_scatter(filtered, "Agent_Rating", "Delivery_Time", "Age_Group", "Agent Rating vs Delivery Time")

# Visual 4: Area
st.subheader("Area — Avg Delivery Time")
area_grp = filtered.groupby("Area", as_index=False)["Delivery_Time"].mean().sort_values("Delivery_Time", ascending=False)
safe_bar(area_grp, "Area", "Delivery_Time", "Avg Delivery Time by Area")

# Visual 5: Category
st.subheader("Category Distribution")
if filtered.empty:
    st.info("No category data to show.")
else:
    fig_cat = px.box(filtered, x="Category", y="Delivery_Time", title="Delivery Time by Category")
    st.plotly_chart(fig_cat, use_container_width=True)

st.markdown("---")
st.caption("If charts are blank: check the diagnostics on the left (column mapping, sample rows, value counts).")
