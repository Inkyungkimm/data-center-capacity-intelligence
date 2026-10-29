"""Interactive dashboard over dbt analytics marts. All values require real data ingestion."""
from __future__ import annotations
import os
import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

st.set_page_config(page_title="Data Center Capacity Intelligence", page_icon="🖥️", layout="wide")
st.title("Data Center Capacity Intelligence")
st.caption("Microsoft Azure VM allocation traces (2020) • real anonymized workload • 14-day observation")
st.info("These are compute allocation workload metrics, not physical data-center MW, PUE, power draw, or permitting metrics.")

@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    import psycopg
    from psycopg.rows import dict_row
    with psycopg.connect(host=os.getenv("PGHOST", "localhost"),
                         port=os.getenv("PGPORT", "5432"),
                         user=os.getenv("PGUSER", "analytics"),
                         password=os.getenv("PGPASSWORD", "analytics_local_only"),
                         dbname=os.getenv("PGDATABASE", "capacity"),
                         row_factory=dict_row) as con:
        with con.cursor() as cur:
            cur.execute(sql)
            return pd.DataFrame(cur.fetchall())

try:
    daily = query("SELECT * FROM analytics.mart_daily_capacity_demand ORDER BY day_index, priority")
    types = query("""SELECT vm_type_id, source_file, total_observed_vm_requests,
                    new_vm_requests_in_window, compatible_machine_ids,
                    min_normalized_cpu_fraction, max_normalized_cpu_fraction
                    FROM analytics.mart_vm_type_demand
                    ORDER BY new_vm_requests_in_window DESC LIMIT 20""")
except Exception as exc:
    st.error("The analytics tables are unavailable. Start PostgreSQL, ingest the public Azure trace, and run `dbt build`.")
    st.code(str(exc))
    st.stop()

if daily.empty:
    st.warning("No records in the analytics marts yet. Run the ingestion and dbt commands in README.")
    st.stop()

total_arrivals = int(daily.new_vm_requests.sum())
peak_daily_overlaps = int(daily.groupby("day_index").vms_overlapping_day.sum().max())
high_new = int(daily.loc[daily.priority_label == 'high', 'new_vm_requests'].sum())
c1,c2,c3 = st.columns(3)
c1.metric("New VM requests (14 days)", f"{total_arrivals:,}")
c2.metric("Highest daily overlap count", f"{peak_daily_overlaps:,}")
c3.metric("High-priority share of arrivals", f"{high_new / total_arrivals:.1%}" if total_arrivals else "N/A")
st.caption("Daily overlap counts every VM active at any point during the day and must not be interpreted as a concurrent peak.")

arrivals = px.bar(daily, x="day_index", y="new_vm_requests", color="priority_label",
                  barmode="stack", labels={"day_index": "Trace day (0–13)",
                  "new_vm_requests": "New requests", "priority_label": "Priority"},
                  title="New VM allocation requests by day")
st.plotly_chart(arrivals, use_container_width=True)

overlap = px.line(daily, x="day_index", y="vms_overlapping_day", color="priority_label",
                  markers=True, title="VMs overlapping each day (NOT instantaneous usage)",
                  labels={"day_index": "Trace day (0–13)",
                          "vms_overlapping_day": "VMs overlapping day", "priority_label": "Priority"})
st.plotly_chart(overlap, use_container_width=True)

st.subheader("Most requested VM types")
if not types.empty:
    plot = types.copy()
    plot["type_key"] = plot["source_file"].astype(str) + " / " + plot["vm_type_id"].astype(str)
    st.plotly_chart(px.bar(plot, x="new_vm_requests_in_window", y="type_key", orientation="h",
                           title="New requests by source-scoped VM type",
                           labels={"new_vm_requests_in_window": "New requests", "type_key": "VM type"}),
                    use_container_width=True)
    st.dataframe(types, use_container_width=True, hide_index=True)
else:
    st.info("No VM type resource profiles loaded.")

st.caption("Attribution: Microsoft Azure Public Dataset, Azure Trace for Packing 2020 (CC BY). See README for original source and Protean paper.")
