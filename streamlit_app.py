import streamlit as st

#tab1, tab2, tab3 = st.tabs()
# st.sidebar.radio("Tabs", ["Records", "Athletes", "Meets"])
pg = st.navigation([st.Page("Pages/1_home.py", title="Home", icon="🏠", default=True), st.Page("Pages/2_records.py", title="All-Time Records", icon="🏆"), st.Page("Pages/3_athletes.py", title="Athlete Directory", icon="🏃"), st.Page("Pages/4_meets.py", title="Meets & Events", icon="🏅"), st.Page("Pages/5_admin.py", title="Admin Access", icon="🔑", visibility="hidden")])