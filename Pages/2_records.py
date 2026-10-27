from io import BytesIO
import math
import re

import pandas as pd
import requests
import streamlit as st

from site_status import stop_if_site_offline
from spreadsheet_config import get_optional_spreadsheet_id
from workbook_source import load_workbook_bytes as load_source_workbook_bytes

stop_if_site_offline()

INDIVIDUAL_SHEET_CANDIDATES = (
    "Athlete Records",
    "Top 50 All-Time Individual PRs",
    "Top 50 All Time Athletes",
)
BOYS_INDIVIDUAL_SHEET_CANDIDATES = (
    "Boys Athlete Records",
    "Boys Individual Records",
    "Boys Records",
    "Boys Individual PRs",
)
GIRLS_INDIVIDUAL_SHEET_CANDIDATES = (
    "Girls Athlete Records",
    "Girls Individual Records",
    "Girls Records",
    "Girls Individual PRs",
)
TEAM_SHEET_CANDIDATES = (
    "Team Records",
    "Top 5 Team Average",
    "Top 10 All Time Teams",
)
BOYS_TEAM_SHEET_CANDIDATES = (
    "Boys Team Records",
    "Boys Team Record",
)
GIRLS_TEAM_SHEET_CANDIDATES = (
    "Girls Team Records",
    "Girls Team Record",
)
COURSE_SHEET_CANDIDATES = ("Amp Records",)
BOYS_COURSE_SHEET_CANDIDATES = (
    "Boys Amp Records",
    "Boys Amphitheater Records",
)
GIRLS_COURSE_SHEET_CANDIDATES = (
    "Girls Amp Records",
    "Girls Amphitheater Records",
)
RECORDS_CACHE_VERSION = 3


@st.cache_data(ttl=3600)
def load_workbook_bytes(spreadsheet_id, cache_version=RECORDS_CACHE_VERSION):
    return load_source_workbook_bytes(spreadsheet_id)


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


def _read_top_n(workbook, sheet_name, cell, fallback):
    if sheet_name is None:
        return fallback, None
    try:
        value = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
            header=None,
            usecols=cell,
            nrows=1,
        ).iloc[0, 0]
        number = float(str(value).strip())
        if not math.isfinite(number) or number < 1 or number != int(number):
            raise ValueError
        return min(int(number), 1000), None
    except (IndexError, OSError, TypeError, ValueError):
        return (
            fallback,
            f"Top N in cell {cell} is invalid; showing up to {fallback} rows.",
        )


def _read_record_view(workbook, sheet_name, cell_range, row_limit, headers):
    if sheet_name is None:
        return pd.DataFrame()
    records = pd.read_excel(
        workbook,
        sheet_name=sheet_name,
        dtype=str,
        header=1,
        nrows=row_limit,
    )
    expected_columns = len(headers)
    start_column, end_column = cell_range.split(":")
    start_index = _column_index(start_column)
    end_index = _column_index(end_column)
    records = records.iloc[:, start_index : end_index + 1]
    if len(records.columns) < expected_columns:
        for index in range(len(records.columns), expected_columns):
            records.insert(index, f"_empty_{index}", "")
    records = records.iloc[:, :expected_columns]
    records.columns = list(headers)
    records = records.dropna(axis=0, how="all").fillna("")
    records = records[
        records.apply(
            lambda row: all(str(value).strip() for value in row)
            and str(row["Rank"]).strip() != "...",
            axis=1,
        )
    ]
    for column in ("Rank", "Year", "Grade"):
        if column in records:
            records[column] = records[column].map(
                lambda value: re.sub(r"\.0+$", "", str(value).strip())
                if value
                else ""
            )
    return records


def _column_index(column):
    index = 0
    for character in column.upper():
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


st.title("All-Time Records")

try:
    workbook = pd.ExcelFile(
        BytesIO(load_workbook_bytes(get_optional_spreadsheet_id()))
    )
except (requests.RequestException, OSError, ValueError) as error:
    st.error("All-time records are temporarily unavailable.")
    st.stop()

individual_sheet = _find_sheet(
    workbook.sheet_names,
    INDIVIDUAL_SHEET_CANDIDATES,
    ("individual", "pr"),
)
boys_individual_sheet = _find_sheet(
    workbook.sheet_names,
    BOYS_INDIVIDUAL_SHEET_CANDIDATES,
    ("boys", "individual"),
)
girls_individual_sheet = _find_sheet(
    workbook.sheet_names,
    GIRLS_INDIVIDUAL_SHEET_CANDIDATES,
    ("girls", "individual"),
)
team_sheet = _find_sheet(
    workbook.sheet_names,
    TEAM_SHEET_CANDIDATES,
    ("team", "average"),
)
boys_team_sheet = _find_sheet(
    workbook.sheet_names,
    BOYS_TEAM_SHEET_CANDIDATES,
    ("boys", "team"),
)
girls_team_sheet = _find_sheet(
    workbook.sheet_names,
    GIRLS_TEAM_SHEET_CANDIDATES,
    ("girls", "team"),
)
course_sheet = _find_sheet(
    workbook.sheet_names,
    COURSE_SHEET_CANDIDATES,
    ("amp", "record"),
)
boys_course_sheet = _find_sheet(
    workbook.sheet_names,
    BOYS_COURSE_SHEET_CANDIDATES,
    ("boys", "amp"),
)
girls_course_sheet = _find_sheet(
    workbook.sheet_names,
    GIRLS_COURSE_SHEET_CANDIDATES,
    ("girls", "amp"),
)

if boys_individual_sheet or girls_individual_sheet:
    individual_views = (
        ("Boys Individual", boys_individual_sheet, "A:G", 50, "E"),
        ("Girls Individual", girls_individual_sheet, "A:G", 50, "E"),
    )
else:
    individual_views = (
        ("Boys Individual", individual_sheet, "A:G", 50, "E"),
        ("Girls Individual", individual_sheet, "H:N", 50, "L"),
    )

if boys_team_sheet or girls_team_sheet:
    team_views = (
        ("Boys Team", boys_team_sheet, "A:F", 10, "E"),
        ("Girls Team", girls_team_sheet, "A:F", 10, "E"),
    )
else:
    team_views = (
        ("Boys Team", team_sheet, "A:F", 10, "E"),
        ("Girls Team", team_sheet, "G:L", 10, "K"),
    )

if boys_course_sheet or girls_course_sheet:
    course_views = (
        ("Boys Amphitheater", boys_course_sheet, "A:F", 100, "E"),
        ("Girls Amphitheater", girls_course_sheet, "A:F", 100, "E"),
    )
else:
    course_views = (
        ("Boys Amphitheater", course_sheet, "A:F", 100, "E"),
        ("Girls Amphitheater", course_sheet, "G:L", 100, "K"),
    )

record_views = (
    *(view + (("Rank", "Athlete", "Time", "Grade", "Year", "Meet", "Course"),) for view in individual_views),
    *(view + (("Rank", "Top-5 Average", "Year", "Meet", "Course", "Team Members"),) for view in team_views),
    *(view + (("Rank", "Athlete", "Team", "Time", "Year", "Meet"),) for view in course_views),
)

tabs = st.tabs([view[0] for view in record_views])
for tab, (label, sheet_name, cell_range, fallback, top_n_cell, headers) in zip(tabs, record_views):
    with tab:
        if sheet_name is None:
            st.error(f"{label} records are temporarily unavailable.")
            continue
        try:
            row_limit, top_n_warning = _read_top_n(
                workbook, sheet_name, top_n_cell, fallback
            )
            if top_n_warning:
                st.warning(top_n_warning)
            records = _read_record_view(
                workbook,
                sheet_name,
                cell_range,
                row_limit,
                headers,
            )
        except (OSError, ValueError) as error:
            st.error(f"{label} records are temporarily unavailable.")
            continue
        if records.empty:
            st.info(f"No {label.lower()} records are available.")
        else:
            st.dataframe(
                records.reset_index(drop=True),
                hide_index=True,
                width="stretch",
                height="content",
            )
