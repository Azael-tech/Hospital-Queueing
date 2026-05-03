"""
views/doctor_view.py
---------------------
Doctor / Nurse action panel — call, serve, cancel patients.
Modules used: streamlit, database, queue_manager
"""

import streamlit as st
from database import (
    init_db, get_next_patient, get_queue,
    call_patient, serve_patient, cancel_patient,
    PRIORITY_COLORS, STATUS_OPEN, STATUS_IN_PROGRESS,
)
from queue_manager import HospitalQueue, compute_wait_time_str


def _patient_card(p: dict, show_actions: bool = True, action_type: str = "call"):
    icon = PRIORITY_COLORS[p["priority"]]
    with st.container(border=True):
        st.markdown(f"### {icon} {p['ticket_number']}  —  {p['full_name']}")
        c1, c2, c3 = st.columns(3)
        c1.write(f"**Age / Sex:** {p['age']} / {p['sex']}")
        c2.write(f"**Priority:** {p['priority']}")
        c3.write(f"**Department:** {p['department']}")
        st.write(f"**Chief Complaint:** {p['chief_complaint']}")
        if p["notes"]:
            st.write(f"**Notes:** {p['notes']}")
        st.caption(f"Contact: {p['contact'] or 'N/A'}  |  Registered: {p['registered_at']}")

        if show_actions:
            btn_col1, btn_col2, _ = st.columns([1, 1, 2])
            if action_type == "call":
                waiting = compute_wait_time_str(p["registered_at"])
                st.caption(f"Has been waiting: **{waiting}**")
                if btn_col1.button(f" Call Patient", key=f"call_{p['id']}"):
                    call_patient(p["id"])
                    st.success(f"Called {p['full_name']} ({p['ticket_number']})")
                    st.rerun()
                if btn_col2.button(" Cancel", key=f"cancel_w_{p['id']}"):
                    cancel_patient(p["id"])
                    st.warning(f"Cancelled {p['ticket_number']}")
                    st.rerun()

            elif action_type == "serve":
                in_prog_dur = compute_wait_time_str(p["called_at"]) if p["called_at"] else "—"
                st.caption(f"In consultation for: **{in_prog_dur}**")
                if btn_col1.button(" Mark as Served", key=f"serve_{p['id']}"):
                    serve_patient(p["id"])
                    st.success(f"Served {p['full_name']} ({p['ticket_number']})")
                    st.rerun()
                if btn_col2.button(" Cancel", key=f"cancel_ip_{p['id']}"):
                    cancel_patient(p["id"])
                    st.warning(f"Cancelled {p['ticket_number']}")
                    st.rerun()


def show():
    init_db()

    st.title(" Doctor / Nurse Panel")
    st.caption("Manage the active queue — call patients, mark as served, or cancel.")

    # ── Quick-call next ──────────────────────────────────────────────────────
    hq = HospitalQueue()
    hq.load_from_db()

    next_p = get_next_patient()

    with st.container(border=True):
        st.subheader("⏭ Next Patient in Queue")
        if next_p:
            icon = PRIORITY_COLORS[next_p["priority"]]
            st.markdown(
                f"**{icon} {next_p['ticket_number']}** — {next_p['full_name']} "
                f"({next_p['priority']}) | {next_p['department']}"
            )
            st.write(f"Complaint: {next_p['chief_complaint']}")
            waiting = compute_wait_time_str(next_p["registered_at"])
            st.caption(f"Waiting: {waiting}")

            if st.button(" Call Next Patient Now", use_container_width=True, type="primary"):
                call_patient(next_p["id"])
                st.success(f" Called {next_p['full_name']} ({next_p['ticket_number']})")
                st.rerun()
        else:
            st.info(" No patients currently waiting in the queue.")

    st.divider()

    # ── In Progress ──────────────────────────────────────────────────────────
    in_progress = get_queue(status_filter=[STATUS_IN_PROGRESS])
    st.subheader(f"⚡ In Progress ({len(in_progress)})")

    if not in_progress:
        st.info("No patients currently in consultation.")
    else:
        for p in in_progress:
            _patient_card(p, show_actions=True, action_type="serve")

    st.divider()

    # ── Full waiting list ────────────────────────────────────────────────────
    waiting = get_queue(status_filter=[STATUS_OPEN])
    st.subheader(f"🟢 Waiting List ({len(waiting)})")

    if not waiting:
        st.info("The waiting queue is empty.")
    else:
        for p in waiting:
            _patient_card(p, show_actions=True, action_type="call")

    st.divider()

    # ── Search by ticket ─────────────────────────────────────────────────────
    st.subheader(" Search Patient by Ticket Number")
    ticket_input = st.text_input("Enter ticket number", placeholder="e.g. E-001")

    if ticket_input:
        from database import get_connection
        conn = get_connection()
        row = conn.execute(
            "SELECT * FROM patients WHERE ticket_number = ?",
            (ticket_input.strip().upper(),)
        ).fetchone()
        conn.close()

        if row:
            p = dict(row)
            icon = PRIORITY_COLORS[p["priority"]]
            with st.container(border=True):
                st.markdown(f"### {icon} {p['ticket_number']} — {p['full_name']}")
                c1, c2 = st.columns(2)
                c1.write(f"**Status:** {p['status']}")
                c1.write(f"**Priority:** {p['priority']}")
                c1.write(f"**Department:** {p['department']}")
                c2.write(f"**Age / Sex:** {p['age']} / {p['sex']}")
                c2.write(f"**Registered:** {p['registered_at']}")
                c2.write(f"**Contact:** {p['contact'] or 'N/A'}")
                st.write(f"**Chief Complaint:** {p['chief_complaint']}")
        else:
            st.warning(f"No patient found with ticket number `{ticket_input}`.")