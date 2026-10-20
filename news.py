import json
import os
import tempfile
from datetime import date
from pathlib import Path

NEWS_FILE = Path(__file__).with_name("news.json")
MAX_HEADLINE_LENGTH = 160
MAX_BODY_LENGTH = 5000
MAX_ENTRIES = 100


def get_news():
    try:
        entries = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            raise ValueError("News file must contain a list")
    except (OSError, ValueError, json.JSONDecodeError):
        return []

    valid_entries = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        headline = str(entry.get("headline", "")).strip()
        body = str(entry.get("body", "")).strip()
        published = str(entry.get("published", "")).strip()
        if headline and body and published:
            valid_entries.append(
                {
                    "headline": headline[:MAX_HEADLINE_LENGTH],
                    "body": body[:MAX_BODY_LENGTH],
                    "published": published,
                }
            )
    return valid_entries[:MAX_ENTRIES]


def save_news(entries):
    cleaned_entries = []
    for entry in entries[:MAX_ENTRIES]:
        headline = str(entry.get("headline", "")).strip()
        body = str(entry.get("body", "")).strip()
        published = str(entry.get("published", "")).strip()
        if not headline or not body or not published:
            raise ValueError("Every news entry needs a headline, body, and date.")
        cleaned_entries.append(
            {
                "headline": headline[:MAX_HEADLINE_LENGTH],
                "body": body[:MAX_BODY_LENGTH],
                "published": published,
            }
        )

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


def add_news(headline, body, published=None):
    entry = {
        "headline": str(headline).strip(),
        "body": str(body).strip(),
        "published": (published or date.today().isoformat()),
    }
    save_news([entry, *get_news()])
