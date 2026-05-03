import streamlit as st

st.set_page_config(
    page_title="MedQueue — Hospital Queueing System",
    layout="wide",
    initial_sidebar_state="expanded",
)

from views import registration, queue_dashboard, doctor_view, analytics

PAGES = {
    " Register Patient": registration.show,
    " Queue Dashboard": queue_dashboard.show,
    " Doctor / Nurse View": doctor_view.show,
    " Analytics": analytics.show,
}


def main():
    st.sidebar.title("MedQueue")
    st.sidebar.caption("Hospital Queueing System")
    st.sidebar.divider()

    page = st.sidebar.radio("Navigation", list(PAGES.keys()))
    st.sidebar.divider()
    st.sidebar.caption("Final Exam Project — Group Output")

    PAGES[page]()


if __name__ == "__main__":
    main()

def print_hi(name):
    print(f'Hi, {name}')  # Press F9 to toggle the breakpoint.


if __name__ == '__main__':
    print_hi('PyCharm')


