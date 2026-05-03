"""
views/analytics.py
-------------------
Analytics & reporting page.
Modules used: streamlit, pandas, plotly.express, datetime, database
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from database import init_db, get_queue, get_stats, PRIORITY_COLORS


def show():
    init_db()

    st.title(" Analytics & Reports")
    st.caption(f"Data as of {datetime.datetime.now().strftime('%B %d, %Y  %I:%M %p')}")

    stats = get_stats()

    # ── Top KPI metrics ──────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Patients",   stats["total"])
    m2.metric(" Waiting",       stats["waiting"])
    m3.metric(" In Progress",   stats["in_progress"])
    m4.metric(" Served",        stats["served"])
    m5.metric(" Avg Wait (min)", stats["avg_wait_min"])

    st.divider()

    # ── Charts row ───────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    # Priority distribution pie
    with col1:
        st.subheader("Priority Distribution")
        if stats["by_priority"]:
            priority_df = pd.DataFrame(stats["by_priority"])
            priority_df.columns = ["Priority", "Count"]
            color_map = {"EMERGENCY": "#e74c3c", "URGENT": "#f39c12", "REGULAR": "#2ecc71"}
            fig = px.pie(
                priority_df,
                names="Priority",
                values="Count",
                color="Priority",
                color_discrete_map=color_map,
                hole=0.4,
            )
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data yet.")

    # Department bar chart
    with col2:
        st.subheader("Patients by Department")
        if stats["by_dept"]:
            dept_df = pd.DataFrame(stats["by_dept"])
            dept_df.columns = ["Department", "Count"]
            fig2 = px.bar(
                dept_df,
                x="Count",
                y="Department",
                orientation="h",
                color="Count",
                color_continuous_scale="Teal",
            )
            fig2.update_layout(margin=dict(t=0, b=0, l=0, r=0), coloraxis_showscale=False)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No data yet.")

    # Hourly patient volume
    st.subheader("Hourly Patient Volume")
    if stats["hourly"]:
        hourly_df = pd.DataFrame(stats["hourly"])
        hourly_df.columns = ["Hour", "Count"]
        hourly_df["Hour"] = hourly_df["Hour"].apply(
            lambda h: datetime.time(int(h)).strftime("%I:00 %p")
        )
        fig3 = px.line(
            hourly_df,
            x="Hour",
            y="Count",
            markers=True,
            line_shape="spline",
            color_discrete_sequence=["#3498db"],
        )
        fig3.update_layout(
            xaxis_title="Hour of Day",
            yaxis_title="Patients Registered",
            margin=dict(t=10, b=0),
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No hourly data yet.")

    st.divider()

    # ── Status breakdown ─────────────────────────────────────────────────────
    st.subheader("Status Summary")
    status_data = {
        "Status": ["Waiting", "In Progress", "Served", "Cancelled"],
        "Count":  [
            stats["waiting"],
            stats["in_progress"],
            stats["served"],
            stats["cancelled"],
        ],
        "Color": ["#2ecc71", "#3498db", "#9b59b6", "#e74c3c"],
    }
    status_df = pd.DataFrame(status_data)
    fig4 = px.bar(
        status_df,
        x="Status",
        y="Count",
        color="Status",
        color_discrete_sequence=status_data["Color"],
    )
    fig4.update_layout(showlegend=False, margin=dict(t=10, b=0))
    st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # ── Full patient log ─────────────────────────────────────────────────────
    st.subheader(" Complete Patient Log")

    all_patients = get_queue()   # no status filter = all records
    if not all_patients:
        st.info("No patient records yet.")
    else:
        log_df = pd.DataFrame(all_patients)

        # Select and rename columns for display
        display_cols = {
            "ticket_number":   "Ticket",
            "full_name":       "Name",
            "age":             "Age",
            "sex":             "Sex",
            "priority":        "Priority",
            "department":      "Department",
            "chief_complaint": "Complaint",
            "status":          "Status",
            "registered_at":   "Registered",
            "called_at":       "Called",
            "served_at":       "Served",
        }
        log_display = log_df[list(display_cols.keys())].rename(columns=display_cols)


        log_display["Priority"] = log_display["Priority"].apply(
            lambda p: f"{PRIORITY_COLORS[p]} {p}"
        )

        # Truncate long complaints
        log_display["Complaint"] = log_display["Complaint"].apply(
            lambda c: c[:35] + "…" if len(c) > 35 else c
        )

        # Filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_status = st.multiselect(
                "Filter by status",
                ["Waiting", "In Progress", "Served", "Cancelled"],
                default=["Waiting", "In Progress", "Served", "Cancelled"],
            )
        with col_f2:
            sel_dept = st.multiselect(
                "Filter by department",
                log_display["Department"].unique().tolist(),
                default=log_display["Department"].unique().tolist(),
            )

        filtered_df = log_display[
            log_display["Status"].isin(sel_status) &
            log_display["Department"].isin(sel_dept)
        ]

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        # ── CSV Export ───────────────────────────────────────────────────────
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇ Export to CSV",
            data=csv_data,
            file_name=f"mediqueue_log_{datetime.date.today()}.csv",
            mime="text/csv",
        )