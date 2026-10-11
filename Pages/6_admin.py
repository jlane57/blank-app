import streamlit as st

from site_status import get_site_status, save_site_status
from spreadsheet_config import get_required_secret

st.title("Admin Portal")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def check_password():
    with st.form("admin_login"):
        password = st.text_input("Enter Password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        configured_password = get_required_secret("ADMIN_PASSWORD")
        if password == configured_password:
            st.session_state.authenticated = True
            st.rerun()
        elif password in {"67", "6767"}:
            st.info("Heehee six seven. Still not the password though, nice try")
        else:
            st.error("Access denied")


if not st.session_state.authenticated:
    st.subheader("Please Enter the Admin Password")
    check_password()
else:
    st.success("Access granted")
    st.write("Welcome, Admin!")

    current = get_site_status()

    with st.container(border=True):
        st.subheader("Website Availability")

        with st.form("website_availability"):
            enabled = st.toggle(
                "Website Is On",
                value=current["enabled"],
                help="Turn this off to show the custom message on public pages.",
            )
            offline_message = st.text_area(
                "Message Shown While the Website Is Off",
                value=current["offline_message"],
                placeholder="Enter the message visitors should see.",
            )
            submitted = st.form_submit_button("Save Settings")

        if submitted:
            try:
                save_site_status(enabled, offline_message)
                st.success("Website settings saved.")
            except OSError as error:
                st.error(f"Could not save website settings: {error}")

    with st.container(border=True):
        st.subheader("Future Admin Controls")
        st.caption("Reserved space for admin tools to be added later.")

    if st.button(
        "Refresh Spreadsheet Data Now",
        help="Clear Streamlit's cached data so the next page load fetches fresh spreadsheet data.",
    ):
        st.cache_data.clear()
        st.success(
            "Data cache cleared. The latest sheet data will load when pages are "
            "next opened or refreshed."
        )