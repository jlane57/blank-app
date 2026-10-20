from io import BytesIO
import re

import pandas as pd
import requests
import streamlit as st

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_export_url, get_spreadsheet_id

stop_if_site_offline()

INDIVIDUAL_SHEET_CANDIDATES = (
    "Top 50 All-Time Individual PRs",
    "Top 50 All Time Athletes",
)
TEAM_SHEET_CANDIDATES = (
    "Top 5 Team Average",
    "Top 10 All Time Teams",
)


@st.cache_data(ttl=3600)
def load_workbook(spreadsheet_id):
    response = requests.get(
        get_spreadsheet_export_url(spreadsheet_id),
        params={"format": "xlsx"},
        timeout=30,
    )
    response.raise_for_status()
    return pd.ExcelFile(BytesIO(response.content))


def _find_sheet(sheet_names, candidates, required_words):
    normalized = {
        re.sub(r"[^a-z0-9]", "", name.casefold()): name
        for name in sheet_names
    }
    for candidate in candidates:
        key = re.sub(r"[^a-z0-9]", "", candidate.casefold())
        if key in normalized:
            return normalized[key]
    for name in sheet_names:
        words = re.sub(r"[^a-z0-9 ]", " ", name.casefold()).split()
        if all(word in words or any(word in item for item in words) for word in required_words):
            return name
    return None


def _read_record_sheet(workbook, sheet_name, row_limit):
    if sheet_name is None:
        return pd.DataFrame()
    return pd.read_excel(
        workbook,
        sheet_name=sheet_name,
        dtype=str,
        header=1,
        nrows=row_limit,
    ).dropna(axis=1, how="all")


st.title("All-Time Records")

selection = st.radio(
    "Choose Records",
    ["Individual PRs", "Team Averages"],
    horizontal=True,
    label_visibility="collapsed",
)

try:
    workbook = load_workbook(get_spreadsheet_id())
    if selection == "Individual PRs":
        sheet_name = _find_sheet(
            workbook.sheet_names,
            INDIVIDUAL_SHEET_CANDIDATES,
            ("individual", "pr"),
        )
        records = _read_record_sheet(workbook, sheet_name, 50)
    else:
        sheet_name = _find_sheet(
            workbook.sheet_names,
            TEAM_SHEET_CANDIDATES,
            ("team", "average"),
        )
        records = _read_record_sheet(workbook, sheet_name, 10)
    if sheet_name is None:
        raise ValueError("No matching records sheet was found.")
except (requests.RequestException, OSError, ValueError) as error:
    st.error(f"Could not load the {selection.lower()} records: {error}")
    st.stop()

if records.empty:
    st.info(f"No {selection.lower()} are available.")
else:
    st.caption(f"Source: {sheet_name}")
    st.dataframe(records, hide_index=True, width="stretch", height="content")
