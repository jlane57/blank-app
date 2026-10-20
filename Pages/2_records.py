from io import BytesIO
import re

import pandas as pd
import requests
import streamlit as st

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_export_url, get_spreadsheet_id

stop_if_site_offline()

INDIVIDUAL_SHEET_CANDIDATES = (
    "Athlete Records",
    "Top 50 All-Time Individual PRs",
    "Top 50 All Time Athletes",
)
TEAM_SHEET_CANDIDATES = (
    "Team Records",
    "Top 5 Team Average",
    "Top 10 All Time Teams",
)
COURSE_SHEET_CANDIDATES = ("Amp Records",)


@st.cache_data(ttl=3600)
def load_workbook_bytes(spreadsheet_id):
    response = requests.get(
        get_spreadsheet_export_url(spreadsheet_id),
        params={"format": "xlsx"},
        timeout=30,
    )
    response.raise_for_status()
    return response.content


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


def _read_record_view(workbook, sheet_name, cell_range, row_limit):
    if sheet_name is None:
        return pd.DataFrame()
    return pd.read_excel(
        workbook,
        sheet_name=sheet_name,
        dtype=str,
        header=1,
        usecols=cell_range,
        nrows=row_limit,
    ).dropna(axis=1, how="all")


st.title("All-Time Records")

try:
    workbook = pd.ExcelFile(
        BytesIO(load_workbook_bytes(get_spreadsheet_id()))
    )
except (requests.RequestException, OSError, ValueError) as error:
    st.error(f"Could not load all-time records: {error}")
    st.stop()

individual_sheet = _find_sheet(
    workbook.sheet_names,
    INDIVIDUAL_SHEET_CANDIDATES,
    ("individual", "pr"),
)
team_sheet = _find_sheet(
    workbook.sheet_names,
    TEAM_SHEET_CANDIDATES,
    ("team", "average"),
)

record_views = (
    ("Boys Individual", individual_sheet, "A:G", 50),
    ("Girls Individual", individual_sheet, "H:N", 50),
    ("Boys Team", team_sheet, "A:F", 10),
    ("Girls Team", team_sheet, "G:L", 10),
    ("Boys Amphitheater", _find_sheet(
        workbook.sheet_names,
        COURSE_SHEET_CANDIDATES,
        ("amp", "record"),
    ), "A:F", 100),
    ("Girls Amphitheater", _find_sheet(
        workbook.sheet_names,
        COURSE_SHEET_CANDIDATES,
        ("amp", "record"),
    ), "G:L", 100),
)

tabs = st.tabs([view[0] for view in record_views])
for tab, (label, sheet_name, cell_range, row_limit) in zip(tabs, record_views):
    with tab:
        if sheet_name is None:
            st.error(f"The workbook does not contain the sheet for {label.lower()} records.")
            continue
        try:
            records = _read_record_view(
                workbook,
                sheet_name,
                cell_range,
                row_limit,
            )
        except (OSError, ValueError) as error:
            st.error(f"Could not load {label.lower()} records: {error}")
            continue
        if records.empty:
            st.info(f"No {label.lower()} records are available.")
        else:
            st.caption(f"Source: {sheet_name}")
            st.dataframe(
                records,
                hide_index=True,
                width="stretch",
                height="content",
            )
