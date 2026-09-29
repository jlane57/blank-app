import streamlit as st

from site_status import get_site_status, save_site_status

st.title("Admin Portal")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

PASSWORD = "1234"


def check_password():
    with st.form("admin_login"):
        password = st.text_input("Enter password", type="password")
        submitted = st.form_submit_button("Sign in")

    if submitted:
        if password == PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Access denied")


if not st.session_state.authenticated:
    st.subheader("Please enter the admin password")
    check_password()
else:
    st.success("Access granted")
    st.write("Welcome, Admin!")

    current = get_site_status()

    with st.container(border=True):
        st.subheader("Website availability")

        with st.form("website_availability"):
            enabled = st.toggle(
                "Website is on",
                value=current["enabled"],
                help="Turn this off to show the custom message on public pages.",
            )
            offline_message = st.text_area(
                "Message shown while the website is off",
                value=current["offline_message"],
                placeholder="Enter the message visitors should see.",
            )
            submitted = st.form_submit_button("Save settings")

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
        "Refresh spreadsheet data now",
        help="Clear Streamlit's cached data so the next page load fetches fresh spreadsheet data.",
    ):
        st.cache_data.clear()
        st.success(
            "Data cache cleared. The latest sheet data will load when pages are "
            "next opened or refreshed."
        )