import json
import os
import tempfile
from datetime import date
from pathlib import Path

from spreadsheet_storage import append_row, read_rows, replace_rows, storage_configured

NEWS_FILE = Path(__file__).with_name("news.json")
NEWS_SHEET = "News"
NEWS_SHEET_COLUMNS = ["Header", "Author", "Date", "Image Link/ID", "Body"]
MAX_HEADLINE_LENGTH = 160
MAX_BODY_LENGTH = 5000
MAX_ENTRIES = 100


def _normalize_image_value(image):
    if image is None:
        return ""
    if isinstance(image, dict):
        for key in ("file_id", "image_id", "id", "display_url", "url", "link"):
            value = image.get(key)
            if value:
                return str(value).strip()
        if image.get("thumbnail_url"):
            return str(image["thumbnail_url"]).strip()
        return ""
    return str(image).strip()


def _normalize_entry(entry):
    if not isinstance(entry, dict):
        return None

    headline = str(entry.get("headline") or entry.get("header") or "").strip()
    body = str(entry.get("body") or "").strip()
    published = str(entry.get("published") or entry.get("date") or "").strip()
    author = str(entry.get("author") or "").strip()
    image = entry.get("image")
    if image is None and entry.get("image_id"):
        image = {"file_id": entry.get("image_id")}
    if not headline or not body or not published:
        return None

    normalized = {
        "headline": headline[:MAX_HEADLINE_LENGTH],
        "body": body[:MAX_BODY_LENGTH],
        "published": published,
        "author": author,
    }
    image_value = _normalize_image_value(image)
    if image_value:
        normalized["image"] = {"file_id": image_value}
    return normalized


def news_sheet_rows(entries):
    rows = [NEWS_SHEET_COLUMNS[:]]
    for entry in entries:
        rows.append(
            [
                str(entry.get("headline", "")).strip(),
                str(entry.get("author", "")).strip(),
                str(entry.get("published", "")).strip(),
                _normalize_image_value(entry.get("image")),
                str(entry.get("body", "")).strip(),
            ]
        )
    return rows


def get_news():
    if storage_configured():
        rows = read_rows(NEWS_SHEET)
        if not rows:
            legacy_entries = _get_local_news()
            if legacy_entries:
                replace_rows(
                    NEWS_SHEET,
                    NEWS_SHEET_COLUMNS,
                    news_sheet_rows(legacy_entries)[1:],
                    allow_destructive=True,
                )
            return legacy_entries
        headers = [str(value).strip() for value in rows[0]]
        indexes = {name: index for index, name in enumerate(headers)}
        entries = []
        for row in rows[1:]:
            values = {
                name: row[indexes[name]] if indexes.get(name, len(row)) < len(row) else ""
                for name in NEWS_SHEET_COLUMNS
            }
            normalized = _normalize_entry(
                {
                    "headline": values["Header"],
                    "author": values["Author"],
                    "published": values["Date"],
                    "image": values["Image Link/ID"],
                    "body": values["Body"],
                }
            )
            if normalized is not None:
                entries.append(normalized)
        return entries[:MAX_ENTRIES]

    return _get_local_news()


def _get_local_news():
    try:
        entries = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError("News file must contain a list")
    except (OSError, ValueError, json.JSONDecodeError):
        return []

    valid_entries = []
    for entry in entries:
        normalized = _normalize_entry(entry)
        if normalized is not None:
            valid_entries.append(normalized)
    return valid_entries[:MAX_ENTRIES]


def save_news(entries, *, allow_delete=False):
    cleaned_entries = []
    for entry in entries[:MAX_ENTRIES]:
        normalized = _normalize_entry(entry)
        if normalized is None:
            raise ValueError("Every news entry needs a headline, body, and date.")
        cleaned_entries.append(normalized)

    if storage_configured():
        replace_rows(
            NEWS_SHEET,
            NEWS_SHEET_COLUMNS,
            news_sheet_rows(cleaned_entries)[1:],
            allow_destructive=allow_delete,
        )
        return

    NEWS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=NEWS_FILE.parent,
            delete=False,
        ) as file:
            json.dump(cleaned_entries, file, indent=2)
            temp_path = Path(file.name)
        os.replace(temp_path, NEWS_FILE)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def add_news(headline, body, published=None, image=None, author=""):
    entry = {
        "headline": str(headline).strip(),
        "body": str(body).strip(),
        "published": (published or date.today().isoformat()),
        "author": str(author).strip(),
    }
    if image:
        entry["image"] = image
    if storage_configured():
        append_row(NEWS_SHEET, NEWS_SHEET_COLUMNS, news_sheet_rows([entry])[1])
        return
    save_news([entry, *get_news()])
