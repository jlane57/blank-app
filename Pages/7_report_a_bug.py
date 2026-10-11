import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from bug_reports import submit_bug_report

st.title("Report a Bug")


def get_optional_secret(name):
    try:
        value = st.secrets[name]
    except (KeyError, StreamlitSecretNotFoundError):
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


report_url = get_optional_secret("BUG_REPORT_WEB_APP_URL")
report_secret = get_optional_secret("BUG_REPORT_SECRET")
if not report_url or not report_secret:
    st.info(
        "Bug reporting is not configured yet. Set "
        "`BUG_REPORT_WEB_APP_URL` and `BUG_REPORT_SECRET` in Streamlit secrets."
    )

with st.form("bug_report_form", clear_on_submit=True):
    st.write("Anonymously submit a website error, bug, or time inaccuracy here.")
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
        with st.spinner("Submitting..."):
            submit_bug_report(report_message, report_url, report_secret)
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"Could not submit the report: {error}")
    else:
        st.success("Thank you. Your anonymous report was submitted.")
