import streamlit as st
import pandas as pd

st.title("Top-50 All-Time Athletes")

CSV_URL = "https://docs.google.com/spreadsheets/d/***REMOVED***/export?format=csv&gid=40739105"

try:
    df = pd.read_csv(CSV_URL, dtype=str)
    df = df.head(51)
except Exception:
    st.error("A data-fetching error occured")

st.table(df)