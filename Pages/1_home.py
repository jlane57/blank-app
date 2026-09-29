import streamlit as st
from site_status import stop_if_site_offline

stop_if_site_offline()

st.title("Welcome to Harrison Cross Country!")
st.write("Use the navigation bar on the left to view team stats")
st.image("Images/group_huddle.jpg")

# col1, col2, col3 = st.columns(3)
# with col1:
#     st.image("Images/group_huddle.jpg")
# with col2:
#     st.image("Images/raiders_athletics_seal.jpeg")
# with col3:
#     st.image("Images/raiders_logo.png")