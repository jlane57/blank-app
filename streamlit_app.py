import streamlit as st

st.set_page_config(
    page_title="Harrison Cross Country",
    page_icon="🏃",
)

st.markdown(
    """
    <style>
    .stApp {
        color: #102A43;
        background:
            linear-gradient(135deg, rgba(245, 130, 32, 0.04), rgba(16, 42, 67, 0.04)),
            rgba(255, 255, 255, 0.03);
    }

    [data-testid="stSidebar"] {
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        bottom: 0 !important;
        width: 21rem !important;
        min-width: 21rem !important;
        max-width: 21rem !important;
        height: 100vh !important;
        height: 100dvh !important;
        overflow-y: auto !important;
        overscroll-behavior: contain;
        background: #193954;
        border-top: 8px solid rgba(245, 130, 32, 0.95);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(-100%) !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    [data-testid="collapsedControl"] {
        display: flex !important;
        position: fixed !important;
        top: 0.75rem !important;
        left: 0.75rem !important;
        z-index: 10000 !important;
    }

    [data-testid="collapsedControl"],
    [data-testid="collapsedControl"] button {
        min-width: 3.25rem !important;
        min-height: 3.25rem !important;
        align-items: center;
        justify-content: center;
        border: 2px solid #FFFFFF !important;
        border-radius: 0.75rem !important;
        background: #F58220 !important;
        box-shadow: 0 3px 12px rgba(16, 42, 67, 0.35) !important;
        color: #102A43 !important;
    }

    [data-testid="collapsedControl"]:hover,
    [data-testid="collapsedControl"] button:hover {
        background: #FFB15C !important;
        transform: scale(1.06);
    }

    [data-testid="collapsedControl"]:focus-visible,
    [data-testid="collapsedControl"] button:focus-visible,
    [data-testid="stSidebar"] [data-testid="stSidebarHeader"] button:focus-visible {
        outline: 3px solid #102A43 !important;
        outline-offset: 2px;
    }

    [data-testid="stSidebar"] [data-testid="stSidebarHeader"] button {
        min-width: 2.75rem !important;
        min-height: 2.75rem !important;
        border: 2px solid rgba(255, 255, 255, 0.8) !important;
        border-radius: 0.65rem !important;
        background: #F58220 !important;
        box-shadow: 0 2px 8px rgba(16, 42, 67, 0.3) !important;
        color: #102A43 !important;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] a {
        color: #FFFFFF;
    }

    [data-testid="stSidebar"] h1 {
        box-sizing: border-box;
        width: 100%;
        color: #FFFFFF;
        font-family: Impact, "Arial Black", Haettenschweiler, sans-serif;
        font-size: 1.7rem;
        font-weight: 900;
        font-style: italic;
        letter-spacing: 0.045em;
        line-height: 1.05;
        text-transform: uppercase;
        text-align: center;
        -webkit-text-stroke: 0.35px rgba(255, 177, 92, 0.9);
        text-shadow:
            2px 2px 0 #B94E00,
            4px 4px 0 rgba(16, 42, 67, 0.55),
            0 6px 14px rgba(0, 0, 0, 0.35);
        margin-bottom: 1rem;
        padding-bottom: 0.65rem;
        border-bottom: 3px solid #F58220;
    }

    [data-testid="stSidebarNavLink"] {
        display: flex;
        align-items: center;
        width: calc(100% - 0.6rem);
        padding: 0.55rem 0.8rem;
        margin: 0.2rem 0.3rem;
        border-radius: 0.7rem;
        line-height: 1.2;
        background: rgba(255, 255, 255, 0.15);
        border: 1px solid rgba(255, 255, 255, 0.15);
    }

    [data-testid="stSidebarNavLink"]:hover {
        background: rgba(255, 255, 255, 0.2);
        border-color: rgba(255, 255, 255, 0.2);
    }

    [data-testid="stSidebarNavLink"] > div,
    [data-testid="stSidebarNavLink"] > span {
        display: flex;
        align-items: center;
        width: 100%;
        text-align: left;
    }

    [data-testid="stSidebarNavLink"] svg {
        margin-right: 0.55rem;
        flex-shrink: 0;
        opacity: 0.9;
    }

    [data-testid="stSidebar"] [data-testid="stImage"] {
        display: block !important;
        width: 225px !important;
        max-width: calc(100% - 1rem) !important;
        margin: 0 auto -2rem !important;
        padding: 0;
        background: transparent;
    }

    [data-testid="stSidebar"] [data-testid="stImage"] button,
    [data-testid="stSidebar"] [data-testid="stImage"] [data-testid="stImageToolbar"] {
        display: none !important;
    }

    [data-testid="stSidebar"] hr {
        border-color: #F58220;
        opacity: 0.75;
    }

    [data-testid="stAppViewContainer"] > .main [data-testid="stMainBlockContainer"] {
        box-sizing: border-box;
        width: min(1200px, calc(100% - 6rem));
        max-width: none;
        margin-inline: auto;
        padding: 3rem 3rem 3rem;
        background: rgba(255, 255, 255, 0.18);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-top: 10px solid #F58220;
        border-left: 8px solid #F58220;
        border-right: 4px solid #193954;
        border-radius: 1rem;
    }

    @media (min-width: 769px) {
        body:has([data-testid="stSidebar"][aria-expanded="true"])
        [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"]:not(:has(.home-hero)) {
            box-sizing: border-box !important;
            width: min(1200px, calc(100vw - 24rem)) !important;
            max-width: none !important;
            margin-left: 21rem !important;
            margin-right: 3rem !important;
        }

        body:has([data-testid="stSidebar"][aria-expanded="false"])
        [data-testid="stAppViewContainer"] [data-testid="stMainBlockContainer"]:not(:has(.home-hero)) {
            box-sizing: border-box !important;
            width: min(1200px, calc(100vw - 6rem)) !important;
            max-width: none !important;
            margin-left: auto !important;
            margin-right: auto !important;
        }
    }

    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {
        background: transparent;
    }

    h1, h2, h3 {
        color: #102A43;
    }

    .main h1 {
        padding: 0 0 0.6rem;
        border-bottom: 8px solid #F58220;
    }

    .main h2 {
        padding: 0.65rem 0.9rem;
        color: #102A43;
        border: 0;
        border-left: 6px solid #F58220;
        border-bottom: 2px solid #193954;
        border-radius: 0.2rem;
        background: rgba(245, 130, 32, 0.08);
    }

    .main hr {
        border-top: 2px dashed #F58220;
        opacity: 1;
    }

    div[data-testid="stTextInput"] [data-baseweb="input"] {
        min-height: 3rem;
        border: 1px solid rgba(25, 57, 84, 0.45);
        border-radius: 0.65rem;
        background: rgba(255, 248, 239, 0.72);
    }

    div[data-testid="stTextInput"] [data-baseweb="input"]:focus-within {
        border-color: #F58220;
        outline: 2px solid rgba(245, 130, 32, 0.2);
    }

    div[data-testid="stTextInput"] [data-baseweb="input"] input {
        border: 0;
        box-shadow: none;
        background: transparent;
    }

    div[data-testid="stSelectbox"] > div > div {
        border: 2px solid #F58220;
        border-radius: 0.65rem;
        background: rgba(255, 248, 239, 0.94);
    }

    div[data-testid="stMetric"] {
        padding: 1rem 1.1rem;
        border: 1px solid rgba(25, 57, 84, 0.18);
        border-left: 6px solid #F58220;
        border-radius: 0.7rem;
        background: rgba(255, 248, 239, 0.88);
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
        border: 2px solid #193954;
        border-top: 6px solid #F58220;
        border-radius: 0.65rem;
        overflow: hidden;
    }

    input[type="radio"],
    input[type="checkbox"] {
        accent-color: #F58220;
    }

    .main a {
        color: #102A43;
    }

    .main a:hover {
        color: #B94E00;
    }

    [data-testid="stSidebar"] a[aria-current="page"] {
        color: #102A43;
        background: #F58220;
        border-left: 5px solid #FFB15C;
        border-radius: 0.35rem;
    }

    div.stButton > button {
        color: #102A43;
        border: 1px solid rgba(25, 57, 84, 0.35);
        background: rgba(255, 255, 255, 0.35);
        justify-content: flex-start;
        text-align: left;
    }

    div.stButton > button:hover {
        color: #102A43;
        border-color: rgba(245, 130, 32, 0.8);
        background: rgba(245, 130, 32, 0.12);
    }

    div.stButton > button:focus-visible {
        outline: 2px solid #F58220;
    }

    @media (max-width: 640px) {
        [data-testid="stAppViewContainer"] > .main [data-testid="stMainBlockContainer"] {
            padding: 2.5rem 1.5rem 2rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# PAGES
HOMEPAGE = st.Page("Pages/1_home.py", title="Home", icon="🏠", default=True)
GIRLSPAGE = st.Page("Pages/8_girls_team.py", title="Girls' Team", icon="🏃")
RECORDSPAGE = st.Page("Pages/2_records.py", title="All-Time Records", icon="🏆")
ATHLETESPAGE = st.Page("Pages/3_athletes.py", title="Athlete Directory", icon="🏃")
YEARSPAGE = st.Page("Pages/4_season_overview.py", title="Data by Season", icon="🗓")
EVENTSPAGE = st.Page("Pages/5_meets.py", title="Meets & Events", icon="🏅")
ADMINPAGE = st.Page("Pages/6_admin.py", title="Admin Access", icon="🔑", visibility="hidden")
BUGREPORTPAGE = st.Page(
    "Pages/7_report_a_bug.py",
    title="Report a Bug",
    icon="🐞",
    visibility="hidden",
)

st.sidebar.title("Harrison Cross Country")
st.sidebar.image("Images/raiders_logo.png", width=225)
st.sidebar.markdown("---")
pg = st.sidebar.page_link(HOMEPAGE)
st.sidebar.page_link(GIRLSPAGE)
st.sidebar.page_link(RECORDSPAGE)
st.sidebar.page_link(ATHLETESPAGE)
st.sidebar.page_link(YEARSPAGE)
st.sidebar.page_link(EVENTSPAGE)
st.sidebar.markdown("---")
st.sidebar.page_link(BUGREPORTPAGE)
st.sidebar.page_link(ADMINPAGE)

pg = st.navigation(
    [
        HOMEPAGE,
        GIRLSPAGE,
        RECORDSPAGE,
        ATHLETESPAGE,
        YEARSPAGE,
        EVENTSPAGE,
        BUGREPORTPAGE,
        ADMINPAGE,
    ],
    position="hidden",
)

pg.run()