from zipfile import BadZipFile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_id
from spreadsheet_data import (
    build_postseason_season_chart_data,
    build_postseason_roster,
    parse_workbook_years,
    sort_meets_by_date,
)

stop_if_site_offline()


@st.cache_data(ttl=3600)
def load_spreadsheet_years(spreadsheet_id):
    response = requests.get(
        f"https://docs.google.com/spreadsheets/d/***REMOVED***/export",
        params={"format": "xlsx"},
        timeout=30,
    )
    response.raise_for_status()
    parsed_data = parse_workbook_years(response.content)
    return {
        "years": parsed_data["years"],
        "issues": parsed_data.get("issues", []),
        "schema_version": 2,
    }


st.title("Data by Season")

try:
    year_data = load_spreadsheet_years(get_spreadsheet_id())
except requests.RequestException as error:
    st.error(f"Could not access spreadsheet data: {error}")
    st.stop()
except InvalidFileException as error:
    st.error(f"The spreadsheet export is not a valid Excel workbook: {error}")
    st.stop()
except (BadZipFile, OSError, ValueError, TypeError, KeyError, OverflowError) as error:
    st.error(f"Could not read the spreadsheet workbook: {error}")
    st.stop()

for issue in year_data.get("issues", []):
    st.warning(f"Skipped a year tab: {issue}")

years = sorted(year_data["years"], reverse=True)
if not years:
    st.info("No year tabs using the expected spreadsheet format were found.")
    st.stop()

selected_year = st.selectbox("Season", years)
season = year_data["years"][selected_year]

st.subheader(f"{selected_year} Meets")
meet_rows = sort_meets_by_date(
    [
        {
            "Meet": meet["name"],
            "Team Place": meet["team_place"],
            "Type": meet["type"],
            "Location": meet["location"],
            "Date": meet["date"],
            "Notes": meet["notes"],
            "raw_date": meet["raw_date"],
        }
        for meet in season["meets"]
    ]
)
if meet_rows:
    st.dataframe(
        [
            {key: value for key, value in meet.items() if key != "raw_date"}
            for meet in meet_rows
        ],
        hide_index=True,
        width="stretch",
        height="content",
    )
else:
    st.info("No meets were found for this season.")

st.subheader("Postseason Roster")
roster_rows = build_postseason_roster(year_data["years"], selected_year)
if roster_rows:
    st.dataframe(
        [
            {
                key: athlete[key]
                for key in ("Rank", "Athlete", "Grade", "PR", "Meet", "Improvement")
            }
            for athlete in roster_rows
        ],
        hide_index=True,
        width="stretch",
        height="content",
    )
else:
    st.info("No bolded athlete names were found in this season.")

st.subheader("Postseason 5K Progression")
progression_rows = build_postseason_season_chart_data(
    year_data["years"],
    selected_year,
)
if progression_rows:
    progression_data = pd.DataFrame(progression_rows)
    event_order = list(dict.fromkeys(progression_data["event"]))
    athletes = sorted(progression_data["athlete"].unique(), key=str.casefold)
    color_palette = px.colors.qualitative.Dark24
    figure = go.Figure()

    for index, athlete_name in enumerate(athletes):
        athlete_data = progression_data[
            progression_data["athlete"] == athlete_name
        ]
        figure.add_trace(
            go.Scatter(
                x=athlete_data["event"],
                y=athlete_data["seconds"],
                mode="lines+markers",
                name=athlete_name,
                line={
                    "color": color_palette[index % len(color_palette)],
                    "width": 2,
                },
                marker={
                    "size": 11,
                    "symbol": athlete_data["marker"],
                    "line": {"width": 1, "color": "white"},
                },
                customdata=athlete_data[["meet", "date", "time", "type"]],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{customdata[0]}<br>"
                    "Date: %{customdata[1]}<br>"
                    "Time: %{customdata[2]}<br>"
                    "Meet Type: %{customdata[3]}<extra></extra>"
                ),
            )
        )

    minimum = min(progression_data["seconds"])
    maximum = max(progression_data["seconds"])
    tick_interval = 30
    tick_start = int(minimum // tick_interval) * tick_interval
    tick_end = int(maximum // tick_interval + 1) * tick_interval
    tick_values = list(range(tick_start, tick_end + 1, tick_interval))
    figure.update_layout(
        template="plotly_white",
        height=500,
        legend_title_text="Athlete",
        margin={"t": 25, "r": 20, "b": 100, "l": 25},
        xaxis_title="Meet (Chronological)",
        yaxis_title="5K Time",
    )
    figure.update_xaxes(
        categoryorder="array",
        categoryarray=event_order,
        tickangle=-35,
        showgrid=False,
    )
    figure.update_yaxes(
        tickmode="array",
        tickvals=tick_values,
        ticktext=[f"{value // 60:02d}:{value % 60:02d}" for value in tick_values],
        gridcolor="#D9E2EC",
        zeroline=False,
    )
    st.plotly_chart(figure, width="stretch")
else:
    st.info("No timed postseason 5K results were found for this season.")

st.subheader("Coaches:")
st.caption("To be updated.")

st.subheader("Postseason Results:")
st.caption("To be updated.")

st.subheader("Notes:")
st.caption("To be updated.")
