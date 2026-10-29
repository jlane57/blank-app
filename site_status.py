import json
from html import escape
import os
import tempfile
from pathlib import Path

import requests
import streamlit as st

from spreadsheet_storage import read_rows, replace_rows, storage_configured, update_key_values

STATUS_FILE = Path(__file__).with_name("site_status.json")
STATUS_SHEET = "Site Settings"
STATUS_HEADERS = ("Key", "Value")
DEFAULT_MESSAGE = "The website is temporarily unavailable. Please check back soon."
DEFAULT_BANNER_MESSAGE = "Welcome to Harrison Cross Country."
MAX_STATUS_MESSAGE_LENGTH = 1000


def get_site_status():
    try:
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
            }
            return {
                "enabled": values.get("enabled", "TRUE").upper() == "TRUE",
                "offline_message": values.get("offline_message", DEFAULT_MESSAGE),
                "banner_enabled": values.get("banner_enabled", "FALSE").upper() == "TRUE",
                "banner_message": values.get("banner_message", DEFAULT_BANNER_MESSAGE),
            }
    except (OSError, ValueError, RuntimeError, requests.RequestException):
        pass

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
    try:
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
    except (OSError, ValueError, RuntimeError) as error:
        raise RuntimeError("Could not save settings to Google Sheets.") from error

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


def _css_string(text):
    """Escape text so it can sit safely inside a double-quoted CSS string."""
    escaped = []
    for char in str(text):
        if char in ('"', "\\"):
            escaped.append("\\" + char)
        elif char in ("<", ">", "&"):
            escaped.append(f"\\{ord(char):x} ")
        elif char in ("\n", "\r"):
            escaped.append("\\A ")
        else:
            escaped.append(char)
    return "".join(escaped)


def render_site_banner():
    status = get_site_status()
    if not status["banner_enabled"]:
        return

    message = status["banner_message"]
    css_message = _css_string(message)
    # The visible banner is drawn on body::before so it is pinned to the very
    # top of the browser window and spans the full width, whatever Streamlit
    # container it would otherwise sit in. Everything else is pushed down by
    # --banner-h (measured in streamlit_app.py) so nothing is covered.
    st.markdown(
        f"""
        <style>
        :root {{
            --banner-h: 3.5rem;
        }}

        html body::before {{
            content: "{css_message}";
            content: "{css_message}" / "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            z-index: 2147483000;
            box-sizing: border-box;
            width: 100%;
            margin: 0;
            padding: 0.9rem clamp(1rem, 4vw, 4rem);
            border-bottom: 5px solid #F58220;
            background: #102A43;
            color: #FFFFFF;
            font-size: clamp(1rem, 1.4vw, 1.2rem);
            font-weight: 800;
            line-height: 1.4;
            text-align: center;
            overflow-wrap: anywhere;
        }}

        html body .stApp {{
            box-sizing: border-box;
            padding-top: var(--banner-h);
        }}

        html body [data-testid="stHeader"] {{
            top: var(--banner-h) !important;
        }}

        html body [data-testid="stSidebar"] {{
            top: var(--banner-h) !important;
            height: calc(100vh - var(--banner-h)) !important;
            height: calc(100dvh - var(--banner-h)) !important;
        }}

        html body [data-testid="collapsedControl"],
        html body [data-testid="stSidebarCollapsedControl"] {{
            top: calc(var(--banner-h) + 1.5rem) !important;
        }}

        .site-wide-banner {{
            position: absolute;
            width: 1px;
            height: 1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
        }}
        </style>
        <div class="site-wide-banner" role="status">{escape(message)}</div>
        """,
        unsafe_allow_html=True,
    )


def stop_if_site_offline():
    status = get_site_status()
    if not status["enabled"]:
        st.title("Temporarily unavailable")
        st.info(status["offline_message"])
        st.stop()