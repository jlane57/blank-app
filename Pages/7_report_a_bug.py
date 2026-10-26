import requests
import streamlit as st

from bug_reports import submit_bug_report
from spreadsheet_storage import storage_configured

st.title("Report a Bug")


try:
    configured = storage_configured()
except (ValueError, RuntimeError):
    configured = False
if not configured:
    st.info("Bug reporting is not configured yet. Ask an administrator to finish setup.")

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
        disabled=not configured,
    )

if report_submitted:
    try:
        with st.spinner("Submitting..."):
            submit_bug_report(report_message)
    except (requests.RequestException, RuntimeError, ValueError) as error:
        st.error(f"Could not submit the report: {error}")
    else:
        st.success("Thank you. Your anonymous report was submitted.")
