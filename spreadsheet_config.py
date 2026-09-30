import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


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
    return get_required_secret("SPREADSHEET_ID").strip()