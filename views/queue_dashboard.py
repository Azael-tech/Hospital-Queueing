"""
views/queue_dashboard.py
------------------------
Live queue monitor page.
Modules used: streamlit, pandas, datetime, queue_manager, database
"""

import streamlit as st
import pandas as pd
import datetime
from database import get_queue, init_db, PRIORITY_COLORS, STATUS_OPEN, STATUS_IN_PROGRESS
from queue_manager import HospitalQueue, compute_wait_time_str


def show():
    init_db()

    st.title(" Live Queue Dashboard")
    st.caption("Auto-refreshes every 30 seconds. Hit Refresh to update immediately.")

    col_ref, col_auto = st.columns([1, 3])
    with col_ref:
        if st.button(" Refresh Now", use_container_width=True):
            st.rerun()
    with col_auto:
        auto = st.toggle("Auto-refresh (30s)", value=False)

    if auto:
        import time
        st.info("Auto-refresh is on. The page will reload every 30 seconds.")
        time.sleep(30)
        st.rerun()

    st.divider()

    # ── Build priority queue from DB ─────────────────────────────────────────
    hq = HospitalQueue()
    hq.load_from_db()

    waiting_patients    = get_queue(status_filter=[STATUS_OPEN])
    in_progress_patients = get_queue(status_filter=[STATUS_IN_PROGRESS])

    # ── Summary metrics ──────────────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(" Waiting",     len(waiting_patients))
    m2.metric(" In Progress", len(in_progress_patients))
    m3.metric(" Queue Size",  hq.size())

    # Next patient
    next_p = hq.peek()
    if next_p:
        m4.metric("⏭ Next Ticket", next_p["ticket_number"])
    else:
        m4.metric("⏭ Next Ticket", "—")

    st.divider()

    # ── In Progress ──────────────────────────────────────────────────────────
    if in_progress_patients:
        st.subheader("⚡ Currently Being Served")
        for p in in_progress_patients:
            icon = PRIORITY_COLORS[p["priority"]]
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 2, 2, 1])
                c1.markdown(f"**{icon} {p['ticket_number']}**")
                c2.write(f"**{p['full_name']}**, {p['age']} y/o {p['sex']}")
                c3.write(f" {p['department']}")
                elapsed = compute_wait_time_str(p["called_at"]) if p["called_at"] else "—"
                c4.caption(f"In progress: {elapsed}")

    # ── Waiting queue ────────────────────────────────────────────────────────
    st.subheader("🟢 Waiting Queue")

    if not waiting_patients:
        st.info("No patients currently waiting. The queue is clear! 🎉")
    else:
        # Build display dataframe
        rows = []
        for idx, p in enumerate(waiting_patients, start=1):
            wait_str   = compute_wait_time_str(p["registered_at"])
            est_wait   = hq.estimate_wait(p["id"])
            rows.append({
                "Position":    idx,
                "Ticket":      p["ticket_number"],
                "Priority":    f"{PRIORITY_COLORS[p['priority']]} {p['priority']}",
                "Patient Name": p["full_name"],
                "Age":         p["age"],
                "Department":  p["department"],
                "Complaint":   p["chief_complaint"][:40] + ("…" if len(p["chief_complaint"]) > 40 else ""),
                "Waiting":     wait_str,
                "Est. Wait":   est_wait,
            })

        df = pd.DataFrame(rows)

        # Color-code by priority using pandas styling
        def highlight_priority(row):
            if "EMERGENCY" in row["Priority"]:
                return ["background-color: #fff0f0"] * len(row)
            elif "URGENT" in row["Priority"]:
                return ["background-color: #fffbea"] * len(row)
            return [""] * len(row)

        styled = df.style.apply(highlight_priority, axis=1)
        st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── Filter view ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader(" Filter by Priority")
    priority_filter = st.multiselect(
        "Select priority levels to display",
        ["EMERGENCY", "URGENT", "REGULAR"],
        default=["EMERGENCY", "URGENT", "REGULAR"],
    )

    filtered = [p for p in waiting_patients if p["priority"] in priority_filter]

    if filtered:
        for p in filtered:
            icon = PRIORITY_COLORS[p["priority"]]
            with st.expander(
                f"{icon} [{p['ticket_number']}] {p['full_name']} — {p['priority']} | {p['department']}"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Age / Sex:** {p['age']} / {p['sex']}")
                    st.write(f"**Contact:** {p['contact'] or 'N/A'}")
                    st.write(f"**Department:** {p['department']}")
                with col2:
                    st.write(f"**Registered:** {p['registered_at']}")
                    st.write(f"**Waiting for:** {compute_wait_time_str(p['registered_at'])}")
                st.write(f"**Chief Complaint:** {p['chief_complaint']}")
                if p["notes"]:
                    st.write(f"**Notes:** {p['notes']}")
    elif priority_filter:
        st.info("No patients match the selected filter.")