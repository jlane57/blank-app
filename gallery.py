import json
import re
from datetime import date
from urllib.parse import quote

import requests

from spreadsheet_config import get_configured_secret, get_spreadsheet_id

GALLERY_SHEET = "Photo Gallery"
GALLERY_HEADERS = (
    "file_id",
    "display_url",
    "thumbnail_url",
    "caption",
    "date_uploaded",
    "category",
    "related_key",
    "photographer",
    "alt_text",
    "approved",
    "featured",
)
MAX_IMAGE_BYTES = 10 * 1024 * 1024
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive"
SHEETS_SCOPE = "https://www.googleapis.com/auth/spreadsheets"


def _credentials():
    raw = get_configured_secret("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw is None:
        raise ValueError("Image storage is not configured.")
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Image storage is not configured.")
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import service_account

        info = json.loads(raw)
        if not isinstance(info, dict) or any(
            not isinstance(info.get(field), str) or not info[field].strip()
            for field in ("client_email", "private_key", "token_uri")
        ):
            raise ValueError("The image service credential is missing required fields.")
    except json.JSONDecodeError as error:
        raise ValueError("The image service credential is invalid.") from error
    except ModuleNotFoundError as error:
        raise RuntimeError("Image storage requires the google-auth dependency.") from error
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=(DRIVE_SCOPE, SHEETS_SCOPE),
    )
    credentials.refresh(Request())
    return credentials


def _auth_headers():
    credentials = _credentials()
    return {"Authorization": "Bearer " + credentials.token}


def _folder_id():
    folder_id = get_configured_secret("GOOGLE_DRIVE_FOLDER_ID")
    if folder_id is None:
        raise ValueError("Image storage is not configured.")
    if not isinstance(folder_id, str) or not folder_id.strip():
        raise ValueError("Image storage is not configured.")
    folder_id = folder_id.strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]+", folder_id):
        raise ValueError("GOOGLE_DRIVE_FOLDER_ID must be a Google Drive folder ID.")
    return folder_id


def _sheets_url(path):
    return (
        "https://sheets.googleapis.com/v4/spreadsheets/"
        f"{get_spreadsheet_id()}/{path}"
    )


def _range_url(cell_range):
    return _sheets_url(f"values/{quote(cell_range, safe='!:$')}")


def get_gallery_entries():
    response = requests.get(
        _range_url(f"{GALLERY_SHEET}!A:K"),
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    values = response.json().get("values", [])
    if not values:
        return []
    header = [str(value).strip() for value in values[0]]
    indexes = {name: index for index, name in enumerate(header)}
    entries = []
    for row in values[1:]:
        entry = {
            name: row[indexes[name]].strip()
            if indexes.get(name) is not None and indexes[name] < len(row)
            else ""
            for name in GALLERY_HEADERS
        }
        if entry["file_id"] and entry["display_url"]:
            entries.append(entry)
    return entries


def _ensure_gallery_headers():
    response = requests.get(
        _range_url(f"{GALLERY_SHEET}!1:1"),
        headers=_auth_headers(),
        timeout=30,
    )
    response.raise_for_status()
    values = response.json().get("values", [])
    if values and values[0][: len(GALLERY_HEADERS)] == list(GALLERY_HEADERS):
        return
    update = requests.put(
        _range_url(f"{GALLERY_SHEET}!A1:K1") + "?valueInputOption=RAW",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"values": [list(GALLERY_HEADERS)]},
        timeout=30,
    )
    update.raise_for_status()


def upload_image(
    data,
    filename,
    caption="",
    photographer="",
    alt_text="",
    category="",
    related_key="",
    featured=False,
):
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Images must be 10 MB or smaller.")
    if not data:
        raise ValueError("Choose an image before uploading.")

    credentials = _credentials()
    metadata = {
        "name": filename,
        "parents": [_folder_id()],
    }
    boundary = "gallery_upload_boundary"
    body = (
        f"--{boundary}\r\n"
        "Content-Type: application/json; charset=UTF-8\r\n\r\n"
        f"{json.dumps(metadata)}\r\n"
        f"--{boundary}\r\n"
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--".encode()
    response = requests.post(
        "https://www.googleapis.com/upload/drive/v3/files"
        "?uploadType=multipart&fields=id,name,mimeType",
        headers={
            "Authorization": "Bearer " + credentials.token,
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
        data=body,
        timeout=60,
    )
    response.raise_for_status()
    file_id = response.json()["id"]

    permission = requests.post(
        f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"type": "anyone", "role": "reader"},
        params={"fields": "id"},
        timeout=30,
    )
    permission.raise_for_status()

    display_url = f"https://drive.google.com/uc?export=view&id={file_id}"
    thumbnail_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w600"
    _ensure_gallery_headers()
    row = [
        file_id,
        display_url,
        thumbnail_url,
        caption.strip(),
        date.today().isoformat(),
        category.strip(),
        related_key.strip(),
        photographer.strip(),
        alt_text.strip() or caption.strip() or filename,
        "TRUE" if featured else "FALSE",
        "TRUE",
    ]
    append = requests.post(
        _range_url(f"{GALLERY_SHEET}!A:K") + ":append?valueInputOption=RAW",
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"values": [row]},
        timeout=30,
    )
    append.raise_for_status()
    return {
        "file_id": file_id,
        "display_url": display_url,
        "thumbnail_url": thumbnail_url,
        "caption": caption.strip(),
        "photographer": photographer.strip(),
        "alt_text": alt_text.strip() or caption.strip() or filename,
    }
