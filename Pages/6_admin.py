import streamlit as st
import requests
from streamlit.errors import StreamlitSecretNotFoundError

from bug_reports import submit_bug_report
from site_status import get_site_status, save_site_status
from spreadsheet_config import get_required_secret

st.title("Admin Portal")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def get_optional_secret(name):
    try:
        value = st.secrets[name]
    except (KeyError, StreamlitSecretNotFoundError):
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


report_tab, admin_tab = st.tabs(["Report a Bug", "Admin Access"])

with report_tab:
    report_url = get_optional_secret("BUG_REPORT_WEB_APP_URL")
    report_secret = get_optional_secret("BUG_REPORT_SECRET")
    if not report_url or not report_secret:
        st.info(
            "Bug reporting is not configured yet. Set "
            "`BUG_REPORT_WEB_APP_URL` and `BUG_REPORT_SECRET` in Streamlit secrets."
        )

    with st.form("bug_report_form"):
        st.write(
            "Anonymously submit a website error, bug, or time inaccuracy here."
        )
        st.caption("Please avoid including personal or sensitive information.")
        report_message = st.text_area(
            "What went wrong?",
            placeholder="Describe what happened and what you expected to happen.",
            max_chars=5000,
        )
        report_submitted = st.form_submit_button(
            "Submit Anonymous Report",
            disabled=not report_url or not report_secret,
        )

    if report_submitted:
        try:
            submit_bug_report(report_message, report_url, report_secret)
        except (requests.RequestException, RuntimeError, ValueError) as error:
            st.error(f"Could not submit the report: {error}")
        else:
            st.success("Thank you. Your anonymous report was submitted.")


with admin_tab:
    def check_password():
        with st.form("admin_login"):
            password = st.text_input("Enter Password", type="password")
            submitted = st.form_submit_button("Sign In")

        if submitted:
            configured_password = get_required_secret("ADMIN_PASSWORD")
            if password == configured_password:
                st.session_state.authenticated = True
                st.rerun()
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