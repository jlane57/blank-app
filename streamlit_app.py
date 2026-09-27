import streamlit as st

# PAGES
HOMEPAGE = st.Page("Pages/1_home.py", title="Home", icon="🏠", default=True)
RECORDSPAGE = st.Page("Pages/2_records.py", title="All-Time Records", icon="🏆")
ATHLETESPAGE = st.Page("Pages/3_athletes.py", title="Athlete Directory", icon="🏃")
EVENTSPAGE = st.Page("Pages/4_meets.py", title="Meets & Events", icon="🏅")
ADMINPAGE = st.Page("Pages/5_admin.py", title="Admin Access", icon="🔑", visibility="hidden")

st.sidebar.title("Harrison Raiders Cross Country")
st.sidebar.image("Images/raiders_logo.png")
st.sidebar.markdown("---")
pg = st.sidebar.page_link(HOMEPAGE)
st.sidebar.page_link(RECORDSPAGE)
st.sidebar.page_link(ATHLETESPAGE)
st.sidebar.page_link(EVENTSPAGE)
st.sidebar.markdown("---")
st.sidebar.page_link(ADMINPAGE)

pg = st.navigation([HOMEPAGE, RECORDSPAGE, ATHLETESPAGE, EVENTSPAGE, ADMINPAGE], position="hidden")

pg.run()