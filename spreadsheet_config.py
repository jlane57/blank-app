import re
from datetime import datetime
from io import BytesIO
from xml.etree import ElementTree
from zipfile import ZipFile

import requests
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

PREVIEW_SPREADSHEET_ID = "***REMOVED***"


def get_required_secret(name):
    try:
        value = st.secrets[name]
    except (KeyError, StreamlitSecretNotFoundError):
        st.error(f"Set {name} in Streamlit secrets to use this app feature.")
        st.stop()

    if not isinstance(value, str) or not value.strip():
        st.error(f"{name} in Streamlit secrets must be a non-empty string.")
        st.stop()

    return value


def get_spreadsheet_id():
    try:
        value = st.secrets["SPREADSHEET_ID"]
    except (KeyError, StreamlitSecretNotFoundError):
        return PREVIEW_SPREADSHEET_ID

    if not isinstance(value, str) or not value.strip():
        st.error("SPREADSHEET_ID in Streamlit secrets must be a non-empty string.")
        st.stop()

    return value.strip()


def _column_index(cell_reference):
    match = re.match(r"([A-Z]+)", cell_reference or "")
    if not match:
        return 0

    column = 0
    for letter in match.group(1):
        column = column * 26 + (ord(letter) - ord("A") + 1)
    return column - 1


def _read_sheet_rows(workbook, sheet_path):
    if sheet_path not in workbook.namelist():
        return []

    shared_strings = []
    if "xl/sharedStrings.xml" in workbook.namelist():
        shared_root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        shared_strings = [
            "".join(node.text or "" for node in item.iter() if node.tag.rsplit("}", 1)[-1] == "t")
            for item in shared_root
        ]

    sheet_root = ElementTree.fromstring(workbook.read(sheet_path))
    rows = []
    for row_node in sheet_root.iter():
        if row_node.tag.rsplit("}", 1)[-1] != "row":
            continue

        values = {}
        for cell in row_node:
            if cell.tag.rsplit("}", 1)[-1] != "c":
                continue

            value_node = next(
                (child for child in cell if child.tag.rsplit("}", 1)[-1] in {"v", "is"}),
                None,
            )
            if value_node is None:
                continue

            cell_reference = cell.attrib.get("r", "A1")
            column_index = _column_index(cell_reference)
            if cell.attrib.get("t") == "s":
                values[column_index] = shared_strings[int(value_node.text or 0)]
            elif cell.attrib.get("t") == "inlineStr":
                values[column_index] = "".join(
                    node.text or "" for node in value_node.iter() if node.tag.rsplit("}", 1)[-1] == "t"
                )
            else:
                values[column_index] = value_node.text or ""

        if not values:
            continue

        width = max(values) + 1
        row = [""] * width
        for index, value in values.items():
            row[index] = value
        rows.append(row)

    return rows


def get_last_updated_note():
    try:
        response = requests.get(
            f"https://docs.google.com/spreadsheets/d/***REMOVED***/export",
            params={"format": "xlsx"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException:
        return {"updated_at": "Unavailable", "last_meet": "Unavailable"}

    try:
        with ZipFile(BytesIO(response.content)) as workbook:
            if "docProps/core.xml" not in workbook.namelist():
                modified_at = None
            else:
                root = ElementTree.fromstring(workbook.read("docProps/core.xml"))
                modified_at = root.findtext(
                    ".//{http://purl.org/dc/terms/}modified"
                )

            if modified_at:
                dt = datetime.fromisoformat(modified_at.replace("Z", "+00:00"))
                updated_at = dt.astimezone().strftime("%b %d, %Y at %I:%M %p")
            else:
                updated_at = "Unavailable"

            last_meet = "Unavailable"
            workbook_root = ElementTree.fromstring(workbook.read("xl/workbook.xml"))
            relationships = ElementTree.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
            targets = {
                item.attrib["Id"]: item.attrib["Target"]
                for item in relationships
                if item.tag.rsplit("}", 1)[-1] == "Relationship"
            }

            sheet_names = [
                item.attrib["name"]
                for item in workbook_root.iter()
                if item.tag.rsplit("}", 1)[-1] == "sheet"
            ]
            years = sorted(
                (int(name) for name in sheet_names if re.fullmatch(r"\d{4}", str(name).strip())),
                reverse=True,
            )
            for year in years:
                sheet_name = str(year)
                sheet = next(
                    (item for item in workbook_root.iter() if item.tag.rsplit("}", 1)[-1] == "sheet" and item.attrib.get("name") == sheet_name),
                    None,
                )
                if sheet is None:
                    continue

                relationship_id = next(
                    (value for key, value in sheet.attrib.items() if key.rsplit("}", 1)[-1] == "id"),
                    None,
                )
                if relationship_id is None:
                    continue

                target = targets.get(relationship_id, "")
                sheet_path = target.lstrip("/")
                if not sheet_path.startswith("xl/"):
                    sheet_path = f"xl/{sheet_path}"

                rows = _read_sheet_rows(workbook, sheet_path)
                if len(rows) < 2:
                    continue

                for column in range(25, 2, -1):
                    if column >= len(rows[1]):
                        continue
                    value = str(rows[1][column]).strip()
                    if value:
                        last_meet = value
                        break
                if last_meet != "Unavailable":
                    break
    except (OSError, ValueError, KeyError, TypeError):
        return {"updated_at": "Unavailable", "last_meet": "Unavailable"}

    return {"updated_at": updated_at, "last_meet": last_meet}