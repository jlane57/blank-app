from streamlit_app import *

st.title("Athletic Directory")

st.text_input("Search for an athlete here", type="search", placeholder="Type athlete name here", icon=":material/search:", label_visibility="collapsed", live=True)