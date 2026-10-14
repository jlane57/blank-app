import streamlit as st

st.title("Girls' Cross Country")
st.subheader("Coming soon")
st.info(
    "Girls' team data is not connected yet. The records, athlete, season, and "
    "meet pages currently display boys' team data."
)
st.page_link(
    "Pages/1_home.py",
    label="Go to the boys' team dashboard",
    icon="🏃",
)
