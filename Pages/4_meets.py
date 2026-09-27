from streamlit_app import *

st.title("Event Database")

st.image("Images/group_huddle.jpg")

st.text_input("Search for an event here", type="search", placeholder="Type event name here", icon=":material/search:", label_visibility="collapsed", live=True)