import requests
import streamlit as st

from spreadsheet_config import get_spreadsheet_export_url


@st.cache_data(ttl=3600)
def load_workbook_bytes(spreadsheet_id=None):
    if spreadsheet_id:
        response = requests.get(
            get_spreadsheet_export_url(spreadsheet_id),
            params={"format": "xlsx"},
            timeout=30,
        )
        response.raise_for_status()
        return response.content
    raise RuntimeError("SPREADSHEET_ID is not configured.")
