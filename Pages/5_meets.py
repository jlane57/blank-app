from difflib import SequenceMatcher
import re
from zipfile import BadZipFile

import pandas as pd
import requests
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_id
from spreadsheet_data import parse_workbook_years, sort_meets_by_date

stop_if_site_offline()


def edit_distance(left, right):
    rows = len(left) + 1
    columns = len(right) + 1
    distance = [[0] * columns for _ in range(rows)]

    for i in range(rows):
        distance[i][0] = i
    for j in range(columns):
        distance[0][j] = j

    for i in range(1, rows):
        for j in range(1, columns):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            distance[i][j] = min(
                distance[i - 1][j] + 1,
                distance[i][j - 1] + 1,
                distance[i - 1][j - 1] + cost,
            )
            if (
                i > 1
                and j > 1
                and left[i - 1] == right[j - 2]
                and left[i - 2] == right[j - 1]
            ):
                distance[i][j] = min(
                    distance[i][j], distance[i - 2][j - 2] + 1
                )

    return distance[-1][-1]


def word_match_score(query_word, name_word):
    if query_word == name_word:
        return 1.0

    shorter, longer = sorted((query_word, name_word), key=len)
    if len(shorter) >= 2 and shorter in longer:
        return 0.88
    if len(query_word) < 3 or len(name_word) < 3:
        return 0.0

    similarity = SequenceMatcher(None, query_word, name_word).ratio()
    allowed_edits = max(1, len(query_word) // 3)
    minimum_similarity = 0.66 if len(query_word) <= 4 else 0.55
    if (
        edit_distance(query_word, name_word) <= allowed_edits
        and similarity >= minimum_similarity
    ):
        return similarity
    return 0.0


def meet_matches_query(query, meet):
    query = str(query or "").strip().casefold()
    if not query:
        return True

    years_in_query = re.findall(r"(?<!\d)\d{4}(?!\d)", query)
    if years_in_query and str(meet["year"]) not in years_in_query:
        return False

    name_query = re.sub(r"(?<!\d)\d{4}(?!\d)", " ", query)
    query_words = re.findall(r"[a-z0-9]+", name_query)
    if not query_words:
        return bool(years_in_query)

    name_words = re.findall(r"[a-z0-9]+", meet["name"].casefold())
    if not name_words:
        return False

    scores = [
        max((word_match_score(word, candidate) for candidate in name_words), default=0)
        for word in query_words
    ]
    matched_scores = [score for score in scores if score > 0]
    required_matches = max(1, (len(query_words) + 1) // 2)
    return (
        len(matched_scores) >= required_matches
        and sum(matched_scores) / len(query_words) >= 0.68
    )


@st.cache_data(ttl=3600)
def load_spreadsheet_years(spreadsheet_id):
    response = requests.get(
        f"https://docs.google.com/spreadsheets/d/***REMOVED***/export",
        params={"format": "xlsx"},
        timeout=30,
    )
    response.raise_for_status()
    parsed_data = parse_workbook_years(response.content)
    return {
        "years": parsed_data["years"],
        "issues": parsed_data.get("issues", []),
    }


try:
    year_data = load_spreadsheet_years(get_spreadsheet_id())
except requests.RequestException as error:
    st.error(f"Could not access spreadsheet data: {error}")
    st.stop()
except (BadZipFile, OSError, ValueError, TypeError, KeyError, OverflowError) as error:
    st.error(f"Could not read the spreadsheet workbook: {error}")
    st.stop()
except InvalidFileException as error:
    st.error(f"The spreadsheet export is not a valid Excel workbook: {error}")
    st.stop()

years = sorted(year_data["years"], reverse=True)
for issue in year_data.get("issues", []):
    st.warning(f"Skipped a year tab: {issue}")
if not years:
    st.info("No year tabs using the expected spreadsheet format were found.")
    st.stop()

meets = []
for year in years:
    for source_meet in year_data["years"][year]["meets"]:
        meet = dict(source_meet)
        meet["results"] = [
            result
            for result in year_data["years"][year]["results"]
            if result["column"] == meet["column"]
        ]
        meets.append(meet)

if not meets:
    st.info("No meets were found in the year tabs.")
    st.stop()

meets_by_year = {
    year: sort_meets_by_date(
        [meet for meet in meets if meet["year"] == year]
    )
    for year in years
}

if "selected_meet" not in st.session_state:
    st.session_state.selected_meet = None

selected = st.session_state.selected_meet

if selected is not None:
    try:
        selected_year = int(selected[0])
        selected_column = int(selected[1])
    except (TypeError, ValueError, IndexError):
        st.session_state.selected_meet = None
        st.rerun()

    meet = next(
        (
            item for item in meets
            if item["year"] == selected_year
            and item["column"] == selected_column
        ),
        None,
    )
    if meet is None:
        st.session_state.selected_meet = None
        st.rerun()

    if st.button("← Back to All Meets"):
        st.session_state.selected_meet = None
        st.rerun()

    st.subheader(f"{meet['name']} ({meet['year']})")
    st.write(f"**Team Place:** {meet['team_place'] or '—'}")
    st.write(
        f"**Type:** {meet['type'] or '—'}  \n"
        f"**Location:** {meet['location'] or '—'}  \n"
        f"**Date:** {meet['date'] or '—'}  \n"
        f"**Notes:** {meet['notes'] or '—'}"
    )

    results = pd.DataFrame(
        [
            {
                "Name": result["name"],
                "Grade": result["grade"],
                "Result": result["result"],
                "_seconds": result["seconds"],
                "_is_varsity": result["is_varsity"],
            }
            for result in meet["results"]
        ],
        columns=["Name", "Grade", "Result", "_seconds", "_is_varsity"],
    )

    if results.empty:
        st.info("No athlete results were recorded for this meet.")
    else:
        if results["_is_varsity"].eq(True).any():
            division = st.radio(
                "Show Results",
                ["ALL", "VARSITY", "JV"],
                horizontal=True,
                label_visibility="collapsed",
                key=f"meet_division_{meet['year']}_{meet['column']}",
            )
            if division == "VARSITY":
                results = results[results["_is_varsity"].eq(True)]
            elif division == "JV":
                results = results[results["_is_varsity"].eq(False)]

        results = results.sort_values(
            "_seconds",
            kind="stable",
            na_position="last",
        )
        st.table(results.drop(columns=["_seconds", "_is_varsity"]).reset_index(drop=True))
else:
    st.title("Event Database")
    search = st.text_input(
        "Search Meets",
        type="search",
        placeholder="Start typing a meet name…",
        live=True,
    ).strip().casefold()
    matches = [meet for meet in meets if meet_matches_query(search, meet)]

    if search:
        if matches:
            st.caption("Matching Meets")
            for meet in matches:
                key = (meet["year"], meet["column"])
                if st.button(
                    f"{meet['name']} ({meet['year']})",
                    key=f"search_{meet['year']}_{meet['column']}",
                    width="stretch",
                ):
                    st.session_state.selected_meet = key
                    st.rerun()
        else:
            st.info("No meets match that search.")

    st.subheader("All Meets")
    for year in years:
        st.markdown(f"**{year}**")
        for meet in meets_by_year[year]:
            key = (meet["year"], meet["column"])
            if st.button(
                meet["name"],
                key=f"meet_{meet['year']}_{meet['column']}",
                width="stretch",
            ):
                st.session_state.selected_meet = key
                st.rerun()
