from io import BytesIO

import pandas as pd
import requests
import streamlit as st

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_export_url, get_spreadsheet_id

stop_if_site_offline()

INDIVIDUAL_SHEET = "Top 50 All Time Athletes"
TEAM_SHEET = "Top 10 All Time Teams"


@st.cache_data(ttl=3600)
def load_records(spreadsheet_id, sheet_name, record_count):
    response = requests.get(
        get_spreadsheet_export_url(spreadsheet_id),
        params={"format": "xlsx"},
        timeout=30,
    )
    response.raise_for_status()
    return pd.read_excel(
        BytesIO(response.content),
        sheet_name=sheet_name,
        dtype=str,
        nrows=record_count,
    )


st.title("All-Time Records")

selection = st.radio(
    "Choose Records",
    ["Individual", "Team"],
    horizontal=True,
    label_visibility="collapsed",
)

if selection == "Individual":
    sheet_name = INDIVIDUAL_SHEET
    record_count = 50
else:
    sheet_name = TEAM_SHEET
    record_count = 10

try:
    records = load_records(get_spreadsheet_id(), sheet_name, record_count)
except (requests.RequestException, OSError, ValueError) as error:
    st.error(f"Could not load '{sheet_name}' from the spreadsheet: {error}")
    st.stop()

st.dataframe(records, hide_index=True, width="stretch", height="content")
