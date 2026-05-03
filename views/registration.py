"""
views/registration.py
----------------------
Patient registration form page.
Modules used: streamlit, datetime, database, queue_manager
"""

import streamlit as st
import datetime
from database import register_patient, get_departments, init_db, PRIORITY_COLORS


def show():
    init_db()

    st.title(" Patient Registration")
    st.caption("Fill in the patient's details below to add them to the queue.")

    departments = get_departments()

    with st.form("registration_form", clear_on_submit=True):
        st.subheader("Personal Information")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            full_name = st.text_input("Full Name *", placeholder="e.g. Juan Dela Cruz")
        with col2:
            age = st.number_input("Age *", min_value=0, max_value=120, value=25, step=1)
        with col3:
            sex = st.selectbox("Sex *", ["Male", "Female", "Other"])

        contact = st.text_input("Contact Number", placeholder="e.g. 09XX-XXX-XXXX")

        st.subheader("Medical Information")
        col4, col5 = st.columns(2)
        with col4:
            department = st.selectbox("Department *", departments)
        with col5:
            priority = st.selectbox(
                "Priority Level *",
                ["REGULAR", "URGENT", "EMERGENCY"],
                help=(
                    "🔴 EMERGENCY — Life-threatening, needs immediate attention\n\n"
                    "🟡 URGENT — Serious but stable\n\n"
                    "🟢 REGULAR — Routine / OPD visit"
                ),
            )

        chief_complaint = st.text_area(
            "Chief Complaint *",
            placeholder="Briefly describe the patient's main reason for visiting...",
            max_chars=300,
        )
        notes = st.text_area(
            "Additional Notes",
            placeholder="Allergies, current medications, etc. (optional)",
            max_chars=500,
        )

        submitted = st.form_submit_button("➕ Register Patient", use_container_width=True)

    if submitted:
        # ── Validation ──────────────────────────────────────────────────────
        errors = []
        if not full_name.strip():
            errors.append("Full name is required.")
        if not chief_complaint.strip():
            errors.append("Chief complaint is required.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            patient = register_patient(
                full_name=full_name.strip(),
                age=int(age),
                sex=sex,
                contact=contact.strip(),
                chief_complaint=chief_complaint.strip(),
                priority=priority,
                department=department,
                notes=notes.strip(),
            )

            icon = PRIORITY_COLORS[priority]
            st.success(f"Patient registered successfully!")
            st.balloons()

            # ── Confirmation card ────────────────────────────────────────────
            with st.container(border=True):
                st.markdown(f"### {icon} Ticket: `{patient['ticket_number']}`")
                c1, c2, c3 = st.columns(3)
                c1.metric("Patient Name", patient["full_name"])
                c2.metric("Priority",     f"{icon} {patient['priority']}")
                c3.metric("Department",   patient["department"])

                st.caption(
                    f"Registered at: {patient['registered_at']}  |  "
                    f"Complaint: {patient['chief_complaint']}"
                )

    # ── Priority legend ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("Priority Level Guide")
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        with st.container(border=True):
            st.markdown("#### 🔴 EMERGENCY")
            st.write("Cardiac arrest, stroke, severe trauma, unconsciousness, difficulty breathing.")
    with col_b:
        with st.container(border=True):
            st.markdown("#### 🟡 URGENT")
            st.write("Severe conditions, and etc.")
    with col_c:
        with st.container(border=True):
            st.markdown("#### 🟢 REGULAR")
            st.write("Routine check-up, minor colds, prescription refill, follow-up consultations.")
