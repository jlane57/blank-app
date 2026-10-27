import json
from datetime import datetime, timezone
from urllib.parse import quote

import requests

from spreadsheet_config import get_configured_secret, get_spreadsheet_id

SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"
SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"


def _service_account_credentials():
    raw = get_configured_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Spreadsheet storage is not configured.")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        info = json.loads(raw)
        if not isinstance(info, dict) or any(
            not isinstance(info.get(field), str) or not info[field].strip()
            for field in ("client_email", "private_key", "token_uri")
        ):
            raise ValueError(
                "The spreadsheet service credential is missing required fields."
            )
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=(SHEETS_SCOPE,)
        )
        credentials.refresh(Request())
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "Spreadsheet storage requires the google-auth dependency."
        ) from error
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise ValueError("The spreadsheet service credential is invalid.") from error
    return credentials


def _headers():
    credentials = _service_account_credentials()
    if not credentials.token:
        raise RuntimeError(
            "Spreadsheet storage authentication did not return an access token."
        )
    return {"Authorization": "Bearer " + credentials.token}


def _values_url(sheet_name, cell_range="A:Z"):
    target = quote(f"{sheet_name}!{cell_range}", safe="!:$")
    return f"{SHEETS_API}/{quote(get_spreadsheet_id(), safe='')}/values/{target}"


def storage_configured():
    raw = get_configured_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw is None or not isinstance(raw, str) or not raw.strip():
        return False
    try:
        _service_account_credentials()
    except RuntimeError as error:
        if str(error) == "Spreadsheet storage requires the google-auth dependency.":
            return False
        raise
    return True


def ensure_sheet(sheet_name):
    metadata = requests.get(
        f"{SHEETS_API}/{quote(get_spreadsheet_id(), safe='')}",
        params={"fields": "sheets.properties.title"},
        headers=_headers(),
        timeout=30,
    )
    metadata.raise_for_status()
    titles = {
        sheet["properties"]["title"]
        for sheet in metadata.json().get("sheets", [])
    }
    if sheet_name in titles:
        return
    response = requests.post(
        f"{SHEETS_API}/{quote(get_spreadsheet_id(), safe='')}:batchUpdate",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        timeout=30,
    )
    response.raise_for_status()


def read_rows(sheet_name, cell_range="A:Z"):
    ensure_sheet(sheet_name)
    response = requests.get(_values_url(sheet_name, cell_range), headers=_headers(), timeout=30)
    response.raise_for_status()
    return response.json().get("values", [])


def ensure_headers(sheet_name, headers):
    ensure_sheet(sheet_name)
    rows = read_rows(sheet_name, "1:1")
    if rows and rows[0][: len(headers)] == list(headers):
        return
    response = requests.put(
        _values_url(sheet_name, f"A1:{chr(64 + len(headers))}1")
        + "?valueInputOption=RAW",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"values": [list(headers)]},
        timeout=30,
    )
    response.raise_for_status()


def append_row(sheet_name, headers, row):
    ensure_headers(sheet_name, headers)
    values = list(row)
    if len(values) != len(headers):
        raise ValueError(f"{sheet_name} row has the wrong number of columns.")
    response = requests.post(
        _values_url(sheet_name, "A:Z")
        + ":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"values": [values]},
        timeout=30,
    )
    response.raise_for_status()


def update_key_values(sheet_name, headers, values_by_key):
    ensure_headers(sheet_name, headers)
    rows = read_rows(sheet_name, "A:Z")
    existing = {
        str(row[0]).strip(): row
        for row in rows[1:]
        if row and str(row[0]).strip()
    }
    for key, value in values_by_key.items():
        existing[str(key)] = [str(key), str(value)]
    ordered_rows = list(existing.values())
    replace_rows(
        sheet_name,
        headers,
        ordered_rows,
        allow_destructive=True,
    )


def replace_rows(sheet_name, headers, rows, *, allow_destructive=False):
    if not allow_destructive:
        raise PermissionError(
            f"Replacing rows in {sheet_name} requires explicit destructive permission."
        )
    ensure_headers(sheet_name, headers)
    existing_rows = read_rows(sheet_name, "A:Z")
    values = [list(headers), *[list(row) for row in rows]]
    if any(len(row) != len(headers) for row in values):
        raise ValueError(f"{sheet_name} contains a row with the wrong number of columns.")
    response = requests.put(
        _values_url(sheet_name, f"A1:{chr(64 + len(headers))}{len(values)}")
        + "?valueInputOption=RAW",
        headers={**_headers(), "Content-Type": "application/json"},
        json={"values": values},
        timeout=30,
    )
    response.raise_for_status()
    if len(existing_rows) > len(values):
        clear = requests.post(
            _values_url(
                sheet_name,
                f"A{len(values) + 1}:Z{len(existing_rows)}",
            )
            + ":clear",
            headers={**_headers(), "Content-Type": "application/json"},
            json={},
            timeout=30,
        )
        clear.raise_for_status()


def utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
