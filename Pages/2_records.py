import streamlit as st
import pandas as pd
from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_id

stop_if_site_offline()

st.title("Top-50 All-Time Athletes")

# Gets a CSV file from the master Google Sheet
CSV_URL = f"https://docs.google.com/spreadsheets/d/{get_spreadsheet_id()}/export?format=csv&gid=40739105"

try:
    df = pd.read_csv(CSV_URL, dtype=str)
    df = df.head(51)
except Exception: # If there's an error, the site will display this message instead of crashing
    st.error("A data-fetching error occured")

st.table(df)