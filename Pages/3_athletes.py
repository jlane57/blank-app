import streamlit as st
from site_status import stop_if_site_offline

stop_if_site_offline()

st.title("Athletic Directory")

st.text_input("Search for an athlete here", type="search", placeholder="Type athlete name here", icon=":material/search:", label_visibility="collapsed", live=True)