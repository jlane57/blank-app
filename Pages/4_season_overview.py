from datetime import date
from zipfile import BadZipFile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_export_url, get_spreadsheet_id
from spreadsheet_data import (
    build_postseason_roster,
    parse_meet_date,
    parse_workbook_years,
    sort_meets_by_date,
)

stop_if_site_offline()


def _truncate_axis_label(label, max_length=18):
    text = str(label or "").strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 1].rstrip() + "…"


def _runner_5k_history(years, runner_name):
    history = []
    for year in sorted(years):
        for athlete in years[year].get("athletes", []):
            if athlete.get("name", "").casefold() != runner_name.casefold():
                continue
            for result in athlete.get("results", []):
                if not result.get("is_5k") or result.get("seconds") is None:
                    continue
                history.append(
                    {
                        "year": year,
                        "name": athlete["name"],
                        "meet": result["meet"],
                        "date": result["date"],
                        "raw_date": result.get("raw_date"),
                        "event": f"{result['meet']} ({result['date']}, {year})",
                        "x_label": _truncate_axis_label(f"{result['meet']} ({result['date']})"),
                        "seconds": result["seconds"],
                        "time": result["result"],
                        "type": result["type"],
                    }
                )
    history.sort(
        key=lambda row: (
            parse_meet_date(row["raw_date"]) is None,
            parse_meet_date(row["raw_date"]) or date.max,
            row["year"],
            row["meet"].casefold(),
        )
    )
    return history


@st.cache_data(ttl=3600)
def load_spreadsheet_years(spreadsheet_id):
    response = requests.get(
        get_spreadsheet_export_url(spreadsheet_id),
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

all_athletes = [
    athlete["name"]
    for athlete in season["athletes"]
    if athlete.get("name")
]
unique_athletes = []
for athlete_name in all_athletes:
    if athlete_name.casefold() not in {item.casefold() for item in unique_athletes}:
        unique_athletes.append(athlete_name)

postseason_athletes = [
    athlete["name"]
    for athlete in season["athletes"]
    if athlete.get("is_postseason") and athlete.get("name")
]

all_roster_rows = build_postseason_roster(year_data["years"], selected_year)

runner_options = ["All", "Postseason Roster", "Top N"]
runner_view = st.selectbox(
    "Display runners",
    runner_options,
    index=runner_options.index("Postseason Roster"),
    key="season_runner_view",
)

if runner_view == "All":
    selected_runner_names = unique_athletes
elif runner_view == "Postseason Roster":
    selected_runner_names = postseason_athletes
else:
    candidate_names = postseason_athletes or unique_athletes
    candidate_stats = []
    for athlete_name in candidate_names:
        history = _runner_5k_history(year_data["years"], athlete_name)
        if not history:
            continue
        candidate_stats.append((athlete_name, min(item["seconds"] for item in history)))
    candidate_stats.sort(key=lambda item: item[1])
    candidate_names = [name for name, _ in candidate_stats]
    max_runners = len(candidate_names)
    top_count = st.number_input(
        "Top runners",
        min_value=1,
        max_value=max_runners,
        value=min(10, max_runners),
        step=1,
        key="season_top_runner_count",
    )
    selected_runner_names = candidate_names[:top_count]

roster_rows = [
    row
    for row in all_roster_rows
    if row["Athlete"].casefold() in {name.casefold() for name in selected_runner_names}
]
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
    st.info("No runners match the current filter.")

season_history = []
for athlete_name in selected_runner_names:
    history = _runner_5k_history(year_data["years"], athlete_name)
    if history:
        season_history.append((athlete_name, history))

if season_history:
    year_palette = {
        str(year): color
        for color, year in zip(px.colors.qualitative.Dark24, sorted(year_data["years"]))
    }
    figure = go.Figure()

    for athlete_name, history in season_history:
        for index, current_row in enumerate(history):
            if index == 0:
                continue
            previous_row = history[index - 1]
            trace = go.Scatter(
                x=[previous_row["x_label"], current_row["x_label"]],
                y=[previous_row["seconds"], current_row["seconds"]],
                mode="lines+markers",
                name=athlete_name,
                legendgroup=athlete_name,
                showlegend=index == 1,
                line={"color": year_palette.get(str(current_row["year"]), "#4C78A8"), "width": 3},
                marker={
                    "size": 9,
                    "symbol": "circle",
                    "color": year_palette.get(str(current_row["year"]), "#4C78A8"),
                    "line": {"width": 1, "color": "white"},
                },
                customdata=[
                    [
                        athlete_name,
                        previous_row["meet"],
                        previous_row["date"],
                        previous_row["time"],
                        previous_row["type"],
                    ],
                    [
                        athlete_name,
                        current_row["meet"],
                        current_row["date"],
                        current_row["time"],
                        current_row["type"],
                    ],
                ],
                hovertemplate=(
                    "<b>%{customdata[0]}</b><br>"
                    "%{customdata[1]}<br>"
                    "Date: %{customdata[2]}<br>"
                    "Time: %{customdata[3]}<br>"
                    "Meet Type: %{customdata[4]}<extra></extra>"
                ),
            )
            figure.add_trace(trace)

    if not figure.data:
        st.info("No timed 5K results were found for the selected runners.")
    else:
        minimum = min(point for trace in figure.data for point in trace.y)
        maximum = max(point for trace in figure.data for point in trace.y)
        tick_interval = 30
        tick_start = int(minimum // tick_interval) * tick_interval
        tick_end = int(maximum // tick_interval + 1) * tick_interval
        tick_values = list(range(tick_start, tick_end + 1, tick_interval))
        figure.update_layout(
            template="plotly_white",
            height=500,
            legend_title_text="Athlete",
            margin={"t": 25, "r": 20, "b": 70, "l": 25},
            xaxis_title="Meet",
            yaxis_title="5K Time",
            hovermode="closest",
        )
        figure.update_xaxes(
            showgrid=False,
            tickangle=-35,
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
    st.info("No timed 5K results were found for the selected runners.")

st.subheader("Coaches:")
st.caption("To be updated.")

st.subheader("Postseason Results:")
st.caption("To be updated.")

st.subheader("Notes:")
st.caption("To be updated.")
