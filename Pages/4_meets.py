import csv
import html
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO

import pandas as pd
import requests
import streamlit as st
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree

from difflib import SequenceMatcher

from site_status import stop_if_site_offline

stop_if_site_offline()

SPREADSHEET_ID = "1cO1crNvALaD4wS-T8Et5RDOSKLiHlWhbTT5vCCp-o3I"

NAME_COLUMN = 0
GRADE_COLUMN = 1
MEET_FIRST_COLUMN = 3  # D
MEET_LAST_COLUMN = 25  # Z
SHEET_COLUMN_COUNT = 26

YEAR_RE = re.compile(r"(?<!\d)\d{4}(?!\d)")
PLACEHOLDERS = {"", "n/a", "na", "---", "--", "-", "—", "–", "dnr", "dnf", "dq"}


def cell(frame, row, column):
    if 0 <= row < frame.shape[0] and 0 <= column < frame.shape[1]:
        return str(frame.iat[row, column]).strip()
    return ""


def normalize_label(value):
    return re.sub(r"[^a-z]", "", str(value).casefold())


def parse_csv(text):
    text = text.lstrip("\ufeff")
    if not text.strip() or text.lstrip().startswith("<"):
        return None

    try:
        rows = list(csv.reader(StringIO(text)))
    except csv.Error:
        return None

    if not rows:
        return None

    width = max(SHEET_COLUMN_COUNT, max(map(len, rows)))
    rows = [row + [""] * (width - len(row)) for row in rows]
    return pd.DataFrame(rows, dtype=str)


def find_sheet_layout(frame):
    """Find the header and section rows independently for each year tab."""
    header_row = next(
        (
            row
            for row in range(frame.shape[0])
            if normalize_label(cell(frame, row, NAME_COLUMN)) == "name"
            and normalize_label(cell(frame, row, GRADE_COLUMN)) == "grade"
        ),
        None,
    )
    if header_row is None:
        return None

    meet_type_row = None
    team_place_row = None

    for row in range(header_row + 1, frame.shape[0]):
        label = normalize_label(cell(frame, row, NAME_COLUMN))
        if label == "meettype":
            meet_type_row = row
        elif label == "teamplace":
            team_place_row = row

    if meet_type_row is None:
        meet_type_row = header_row + 1
    if team_place_row is None:
        team_place_row = meet_type_row + 1

    if team_place_row >= frame.shape[0]:
        return None

    return {
        "header_row": header_row,
        "meet_type_row": meet_type_row,
        "team_place_row": team_place_row,
        "first_athlete_row": team_place_row + 1,
    }


@st.cache_data(ttl=3600)
def download_workbook():
    url = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export"
    response = requests.get(url, params={"format": "xlsx"}, timeout=30)
    response.raise_for_status()
    return response.content


@st.cache_data(ttl=3600)
def discover_year_candidates():
    """Return actual four-digit workbook tab names, newest first."""
    with ZipFile(BytesIO(download_workbook())) as workbook:
        root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
        names = [
            item.attrib["name"]
            for item in root.iter()
            if item.tag.rsplit("}", 1)[-1] == "sheet"
        ]
    return sorted(
        (int(name) for name in names if re.fullmatch(r"\d{4}", name.strip())),
        reverse=True,
    )


@st.cache_data(ttl=3600)
def load_year(year):
    """Read a year tab from the workbook without CSV column/row ambiguity."""
    sheet_name = str(year)
    with ZipFile(BytesIO(download_workbook())) as workbook:
        root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        targets = {
            item.attrib["Id"]: item.attrib["Target"]
            for item in relationships
            if item.tag.rsplit("}", 1)[-1] == "Relationship"
        }
        sheet = next(
            (item for item in root.iter()
             if item.tag.rsplit("}", 1)[-1] == "sheet"
             and item.attrib.get("name") == sheet_name),
            None,
        )
        if sheet is None:
            return None
        relationship_id = next(
            value for key, value in sheet.attrib.items()
            if key.rsplit("}", 1)[-1] == "id"
        )
        target = targets[relationship_id].lstrip("/")
        sheet_path = target if target.startswith("xl/") else f"xl/{target}"

        shared_strings = []
        if "xl/sharedStrings.xml" in workbook.namelist():
            shared_root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
            shared_strings = [
                "".join(node.text or "" for node in item.iter()
                        if node.tag.rsplit("}", 1)[-1] == "t")
                for item in shared_root
            ]
        sheet_root = ElementTree.fromstring(workbook.read(sheet_path))

    rows = []
    for row_node in sheet_root.iter():
        if row_node.tag.rsplit("}", 1)[-1] != "row":
            continue
        values = {}
        for item in row_node:
            if item.tag.rsplit("}", 1)[-1] != "c":
                continue
            match = re.match(r"[A-Z]+", item.attrib.get("r", "A1"))
            column = 0
            for letter in match.group():
                column = column * 26 + ord(letter) - ord("A") + 1
            column -= 1
            value_node = next(
                (child for child in item
                 if child.tag.rsplit("}", 1)[-1] in ("v", "is")),
                None,
            )
            value = ""
            if value_node is not None:
                if item.attrib.get("t") == "s":
                    value = shared_strings[int(value_node.text or 0)]
                elif item.attrib.get("t") == "inlineStr":
                    value = "".join(node.text or "" for node in value_node.iter()
                                    if node.tag.rsplit("}", 1)[-1] == "t")
                else:
                    value = value_node.text or ""
            values[column] = value
        row = [""] * (max(values, default=-1) + 1)
        for column, value in values.items():
            row[column] = value
        rows.append(row)

    width = max(SHEET_COLUMN_COUNT, max(map(len, rows), default=0))
    frame = pd.DataFrame(
        [row + [""] * (width - len(row)) for row in rows], dtype=str
    )

    # Preserve the spreadsheet's A:Z column indexes, including trailing blanks.
    frame = frame.reindex(
        columns=range(max(frame.shape[1], SHEET_COLUMN_COUNT)),
        fill_value="",
    )
    return frame.fillna("").astype(str)


def parse_time(value):
    """Parse MM:SS, HH:MM:SS, or an Excel day-fraction duration."""
    text = str(value).strip()
    if not text:
        return None

    # pandas may render Excel durations as "0 days 00:16:59.000".
    day_match = re.fullmatch(r"(\d+)\s+days?\s+(.+)", text, re.IGNORECASE)
    days = int(day_match.group(1)) if day_match else 0
    if day_match:
        text = day_match.group(2).strip()

    parts = text.split(":")
    if len(parts) in (2, 3):
        try:
            seconds = Decimal(parts[-1])
            if not seconds.is_finite() or not 0 <= seconds < 60:
                return None

            if len(parts) == 2:
                minutes = int(parts[0])
                if minutes < 0:
                    return None
                return Decimal(days * 86400 + minutes * 60) + seconds

            hours = int(parts[0])
            minutes = int(parts[1])
            if hours < 0 or not 0 <= minutes < 60:
                return None
            return Decimal(days * 86400 + hours * 3600 + minutes * 60) + seconds
        except (InvalidOperation, ValueError):
            return None

    # Excel can expose a duration as a fraction of a day.
    try:
        day_fraction = Decimal(text)
        if day_fraction.is_finite() and 0 <= day_fraction <= 1:
            return day_fraction * Decimal(86400)
    except InvalidOperation:
        pass

    return None


def format_time(value):
    """Format elapsed time as MM:SS[.mmm], omitting insignificant zeros."""
    total_seconds = parse_time(value)
    if total_seconds is None:
        return str(value).strip()

    # Excel stores durations as fractions of a day; cap display precision at
    # milliseconds to avoid exposing floating-point storage noise.
    total_seconds = total_seconds.quantize(Decimal("0.001"))
    whole_seconds = int(total_seconds)
    minutes, seconds = divmod(whole_seconds, 60)
    fraction = total_seconds - Decimal(whole_seconds)

    result = f"{minutes:02d}:{seconds:02d}"
    if fraction:
        milliseconds = f"{fraction:.3f}".split(".", 1)[1].rstrip("0")
        result += f".{milliseconds}"
    return result


def _edit_distance(left, right):
    """Compute edit distance, including adjacent-letter transpositions."""
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
                distance[i - 1][j] + 1,       # deletion
                distance[i][j - 1] + 1,       # insertion
                distance[i - 1][j - 1] + cost, # substitution
            )

            if (
                i > 1
                and j > 1
                and left[i - 1] == right[j - 2]
                and left[i - 2] == right[j - 1]
            ):
                distance[i][j] = min(
                    distance[i][j],
                    distance[i - 2][j - 2] + 1,
                )

    return distance[-1][-1]


def _word_match_score(query_word, name_word):
    """Return a similarity score from 0 to 1 for a query/name word pair."""
    if query_word == name_word:
        return 1.0

    shorter, longer = sorted((query_word, name_word), key=len)

    # Useful partials, e.g. "amp" matching "champ".
    if len(shorter) >= 2 and shorter in longer:
        return 0.88

    # Allow misspellings and adjacent-letter swaps.
    if len(query_word) < 3 or len(name_word) < 3:
        return 0.0

    similarity = SequenceMatcher(None, query_word, name_word).ratio()
    edits = _edit_distance(query_word, name_word)
    allowed_edits = max(1, len(query_word) // 3)

    minimum_similarity = 0.66 if len(query_word) <= 4 else 0.55
    if edits <= allowed_edits and similarity >= minimum_similarity:
        return similarity

    return 0.0


def meet_matches_query(query, meet):
    query = str(query or "").strip().casefold()
    if not query:
        return True

    # A typed year is a strict filter, but other words can be in any order.
    years_in_query = re.findall(r"(?<!\d)\d{4}(?!\d)", query)
    if years_in_query and str(meet.get("year", "")) not in years_in_query:
        return False

    name_query = re.sub(r"(?<!\d)\d{4}(?!\d)", " ", query)
    query_words = re.findall(r"[a-z0-9]+", name_query)
    if not query_words:
        return bool(years_in_query)

    name_words = re.findall(
        r"[a-z0-9]+",
        str(meet.get("name", "")).casefold(),
    )
    if not name_words:
        return False

    # Measure each query word against the best-matching meet-name word.
    scores = [
        max((_word_match_score(word, candidate) for candidate in name_words), default=0)
        for word in query_words
    ]

    matched_scores = [score for score in scores if score > 0]
    if not matched_scores:
        return False

    # Require a meaningful match, but allow one of several search words to be
    # misspelled beyond recognition or incidental.
    required_matches = max(1, (len(query_words) + 1) // 2)
    return (
        len(matched_scores) >= required_matches
        and sum(matched_scores) / len(matched_scores) >= 0.68
    )


st.title("Event Database")

try:
    candidates = discover_year_candidates()
except requests.RequestException as error:
    st.error(f"Could not access spreadsheet metadata: {error}")
    st.stop()

if not candidates:
    st.error("Could not find year candidates in the spreadsheet.")
    st.stop()

with ThreadPoolExecutor(max_workers=8) as executor:
    loaded_frames = list(executor.map(load_year, candidates))

frames = {
    year: frame
    for year, frame in zip(candidates, loaded_frames)
    if frame is not None
}
years = sorted(frames, reverse=True)

if not years:
    st.error("No year tabs with meet names in D2:Z2 could be loaded.")
    st.stop()

meets = []
for year in years:
    frame = frames[year]

    # Fixed shared layout: names D2:Z2; type row 3; place row 4;
    # athlete results begin on row 5. Indexes are zero-based.
    layout = {
        "header_row": 1,
        "meet_type_row": 2,
        "team_place_row": 3,
        "first_athlete_row": 4,
    }

    for column in range(MEET_FIRST_COLUMN, MEET_LAST_COLUMN + 1):
        name = cell(frame, layout["header_row"], column)
        if name:
            meets.append({
                "year": year,
                "column": column,
                "name": name,
                "frame": frame,
                "layout": layout,
            })

if not meets:
    st.error("No meet names were found in columns D:Z on the loaded year tabs.")
    st.stop()

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
            item
            for item in meets
            if item["year"] == selected_year
            and item["column"] == selected_column
        ),
        None,
    )

    if meet is None:
        st.session_state.selected_meet = None
        st.rerun()

    if st.button("← Back to all meets"):
        st.session_state.selected_meet = None
        st.rerun()

    frame = meet["frame"]
    column = meet["column"]
    layout = meet["layout"] or {
        "meet_type_row": 2,
        "team_place_row": 3,
        "first_athlete_row": 4,
    }

    st.subheader(f"{meet['name']} ({meet['year']})")
    st.write(
        f"**Type:** {cell(frame, layout['meet_type_row'], column) or '—'}  \n"
        f"**Team place:** {cell(frame, layout['team_place_row'], column) or '—'}"
    )

    first_athlete_row = layout["first_athlete_row"]
    results = pd.DataFrame(
        {
            "Name": [
                cell(frame, row, NAME_COLUMN)
                for row in range(first_athlete_row, frame.shape[0])
            ],
            "Grade": [
                cell(frame, row, GRADE_COLUMN)
                for row in range(first_athlete_row, frame.shape[0])
            ],
            "Result": [
                cell(frame, row, column)
                for row in range(first_athlete_row, frame.shape[0])
            ],
        }
    )

    results["_seconds"] = results["Result"].map(parse_time)
    results = results[
        results["Name"].ne("") & results["_seconds"].notna()
    ].sort_values("_seconds", kind="stable")

    results["Result"] = results["Result"].map(format_time)
    st.table(results.drop(columns="_seconds").reset_index(drop=True))

else:
    search = st.text_input(
        "Search meets",
        placeholder="Start typing a meet name…",
    ).strip().casefold()

    matches = [
        meet for meet in meets
        if meet_matches_query(search, meet)
    ]

    if search:
        if matches:
            st.caption("Matching meets")
            for meet in matches:
                key = (meet["year"], meet["column"])
                if st.button(
                    f"{meet['name']} ({meet['year']})",
                    key=f"search_{meet['year']}_{meet['column']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_meet = key
                    st.rerun()
        else:
            st.info("No meets match that search.")

    st.subheader("All meets")
    for year in years:
        st.markdown(f"**{year}**")
        for meet in (item for item in meets if item["year"] == year):
            key = (meet["year"], meet["column"])
            if st.button(
                meet["name"],
                key=f"meet_{meet['year']}_{meet['column']}",
                use_container_width=True,
            ):
                st.session_state.selected_meet = key
                st.rerun()