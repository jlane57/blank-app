import json
from html import escape
import os
import tempfile
from pathlib import Path

import streamlit as st

from spreadsheet_storage import read_rows, replace_rows, storage_configured, update_key_values

STATUS_FILE = Path(__file__).with_name("site_status.json")
STATUS_SHEET = "Site Settings"
STATUS_HEADERS = ("Key", "Value")
DEFAULT_MESSAGE = "The website is temporarily unavailable. Please check back soon."
DEFAULT_BANNER_MESSAGE = "Welcome to Harrison Cross Country."
MAX_STATUS_MESSAGE_LENGTH = 1000


def get_site_status():
    if storage_configured():
        rows = read_rows(STATUS_SHEET)
        if not rows:
            legacy_status = _get_local_status()
            replace_rows(
                STATUS_SHEET,
                STATUS_HEADERS,
                [
                    ["enabled", "TRUE" if legacy_status["enabled"] else "FALSE"],
                    ["offline_message", legacy_status["offline_message"]],
                    ["banner_enabled", "TRUE" if legacy_status["banner_enabled"] else "FALSE"],
                    ["banner_message", legacy_status["banner_message"]],
                ],
                allow_destructive=True,
            )
            return legacy_status
        values = {
            str(row[0]).strip(): str(row[1]).strip()
            for row in rows[1:]
            if len(row) >= 2 and str(row[0]).strip()
        } if rows else {}
        return {
            "enabled": values.get("enabled", "TRUE").upper() == "TRUE",
            "offline_message": values.get("offline_message", DEFAULT_MESSAGE),
            "banner_enabled": values.get("banner_enabled", "FALSE").upper() == "TRUE",
            "banner_message": values.get("banner_message", DEFAULT_BANNER_MESSAGE),
        }

    return _get_local_status()


def _get_local_status():
    try:
        status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        if not isinstance(status, dict):
            raise ValueError("Invalid status file")
        return {
            "enabled": status.get("enabled") is not False,
            "offline_message": str(status.get("offline_message", DEFAULT_MESSAGE)),
            "banner_enabled": status.get("banner_enabled") is True,
            "banner_message": str(
                status.get("banner_message", DEFAULT_BANNER_MESSAGE)
            ),
        }
    except (OSError, ValueError, json.JSONDecodeError):
        return {
            "enabled": True,
            "offline_message": DEFAULT_MESSAGE,
            "banner_enabled": False,
            "banner_message": DEFAULT_BANNER_MESSAGE,
        }


def save_site_status(
    enabled,
    offline_message,
    banner_enabled=False,
    banner_message=DEFAULT_BANNER_MESSAGE,
):
    status = {
        "enabled": bool(enabled),
        "offline_message": (
            str(offline_message).strip() or DEFAULT_MESSAGE
        )[:MAX_STATUS_MESSAGE_LENGTH],
        "banner_enabled": bool(banner_enabled),
        "banner_message": (
            str(banner_message).strip() or DEFAULT_BANNER_MESSAGE
        )[:MAX_STATUS_MESSAGE_LENGTH],
    }
    if storage_configured():
        update_key_values(
            STATUS_SHEET,
            STATUS_HEADERS,
            {
                "enabled": "TRUE" if status["enabled"] else "FALSE",
                "offline_message": status["offline_message"],
                "banner_enabled": "TRUE" if status["banner_enabled"] else "FALSE",
                "banner_message": status["banner_message"],
            },
        )
        return

    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=STATUS_FILE.parent,
            delete=False,
        ) as file:
            json.dump(status, file)
            temp_path = Path(file.name)

        os.replace(temp_path, STATUS_FILE)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def render_site_banner():
    status = get_site_status()
    if status["banner_enabled"]:
        st.markdown(
            (
                '<div class="site-wide-banner" role="status">'
                f"{escape(status['banner_message'])}"
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def stop_if_site_offline():
    status = get_site_status()
    if not status["enabled"]:
        st.title("Temporarily unavailable")
        st.info(status["offline_message"])
        st.stop()