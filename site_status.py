import json
import os
import tempfile
from pathlib import Path

import streamlit as st

STATUS_FILE = Path(__file__).with_name("site_status.json")
DEFAULT_MESSAGE = "The website is temporarily unavailable. Please check back soon."


def get_site_status():
    try:
        status = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        if not isinstance(status, dict):
            raise ValueError("Invalid status file")
        return {
            "enabled": status.get("enabled") is not False,
            "offline_message": str(status.get("offline_message", DEFAULT_MESSAGE)),
        }
    except (OSError, ValueError, json.JSONDecodeError):
        return {"enabled": True, "offline_message": DEFAULT_MESSAGE}


def save_site_status(enabled, offline_message):
    status = {
        "enabled": bool(enabled),
        "offline_message": str(offline_message).strip() or DEFAULT_MESSAGE,
    }
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


def stop_if_site_offline():
    status = get_site_status()
    if not status["enabled"]:
        st.title("Temporarily unavailable")
        st.info(status["offline_message"])
        st.stop()