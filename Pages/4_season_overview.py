from datetime import date
from zipfile import BadZipFile

import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_export_url, get_spreadsheet_id
from spreadsheet_data import (
    build_athlete_5k_chart_data,
    build_postseason_roster,
    parse_meet_date,
    parse_workbook_years,
    sort_meets_by_date,
)

stop_if_site_offline()


def _truncate_axis_label(label, max_length=18):
    text = str(label or "").strip()
    return text[:max_length]


def _build_runner_5k_index(years):
    histories = {}
    for year, season in years.items():
        for athlete in season.get("athletes", []):
            for result in athlete.get("results", []):
                if (
                    "5k" not in str(result.get("type", "")).casefold()
                    or result.get("seconds") is None
                ):
                    continue
                runner_name = athlete["name"].casefold()
                histories.setdefault(runner_name, []).append(
                    {
                        "year": year,
                        "column": result["column"],
                        "name": athlete["name"],
                        "meet": result["meet"],
                        "date": result["date"],
                        "raw_date": result.get("raw_date"),
                        "seconds": result["seconds"],
                        "time": result["result"],
                        "result": result["result"],
                        "type": result["type"],
                        "is_5k": result["is_5k"],
                    }
                )
    for history in histories.values():
        history.sort(
            key=lambda row: (
                parse_meet_date(row["raw_date"]) is None,
                parse_meet_date(row["raw_date"]) or date.max,
                row["year"],
                row["meet"].casefold(),
            )
        )
        markers = {
            (int(result["year"]), result["column"]): result["marker"]
            for result in build_athlete_5k_chart_data(history)
        }
        for result in history:
            result["marker"] = markers[(result["year"], result["column"])]
    return histories


@st.cache_data(ttl=3600)
def load_spreadsheet_years(spreadsheet_id):
    response = requests.get(
        get_spreadsheet_export_url(spreadsheet_id),
        params={"format": "xlsx"},
        timeout=30,
    )
    response.raise_for_status(    )
    parsed_data = parse_workbook_years(response.content)
    return {
        "years": parsed_data["years"],
        "runner_5k_index": _build_runner_5k_index(parsed_data["years"]),
        "issues": parsed_data.get("issues", []),
        "schema_version": 3,
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
runner_5k_index = year_data["runner_5k_index"]

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
seen_athletes = set()
for athlete_name in all_athletes:
    athlete_key = athlete_name.casefold()
    if athlete_key not in seen_athletes:
        unique_athletes.append(athlete_name)
        seen_athletes.add(athlete_key)

postseason_athletes = [
    athlete["name"]
    for athlete in season["athletes"]
    if athlete.get("is_postseason") and athlete.get("name")
]

all_roster_rows = build_postseason_roster(
    year_data["years"],
    selected_year,
    postseason_only=False,
)

runner_options = ["All", "Postseason Roster"]
if unique_athletes:
    runner_options.append("Top N")
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
        history = runner_5k_index.get(athlete_name.casefold(), [])
        if not history:
            continue
        candidate_stats.append((athlete_name, min(item["seconds"] for item in history)))
    candidate_stats.sort(key=lambda item: item[1])
    candidate_names = [name for name, _ in candidate_stats] or candidate_names
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
    roster_table_rows = [
        {
            key: athlete[key]
            for key in ("Athlete", "Grade")
        }
        | {
            "Current PR": athlete["PR"],
            "PR Meet": athlete["Meet"],
            "YtY Improvement": athlete["Improvement"],
        }
        for athlete in roster_rows
    ]
    st.dataframe(
        roster_table_rows,
        hide_index=True,
        width="stretch",
        height=35 * len(roster_table_rows) + 38,
    )
else:
    st.info("No runners match the current filter.")

chart_runner_names = st.multiselect(
    "Athletes to compare",
    options=selected_runner_names,
    default=selected_runner_names,
    key=f"season_chart_athletes_{selected_year}",
)

season_history = []
for athlete_name in chart_runner_names:
    history = [
        result
        for result in runner_5k_index.get(athlete_name.casefold(), [])
        if result["year"] == selected_year
    ]
    if history:
        season_history.append((athlete_name, history))

if season_history:
    event_data = {}
    for _, history in season_history:
        for result in history:
            event_data[result["column"]] = result
    event_order = sorted(
        event_data,
        key=lambda column: (
            parse_meet_date(event_data[column]["raw_date"]) is None,
            parse_meet_date(event_data[column]["raw_date"]) or date.max,
            event_data[column]["meet"].casefold(),
        ),
    )
    event_positions = {column: index for index, column in enumerate(event_order)}
    event_labels = [
        _truncate_axis_label(event_data[column]["meet"], 5)
        for column in event_order
    ]
    color_palette = px.colors.qualitative.Dark24
    figure = go.Figure()

    for index, (athlete_name, history) in enumerate(season_history):
        history.sort(key=lambda result: event_positions[result["column"]])
        color = color_palette[index % len(color_palette)]
        figure.add_trace(
            go.Scatter(
                x=[event_positions[result["column"]] for result in history],
                y=[result["seconds"] for result in history],
                mode="lines+markers",
                name=athlete_name,
                line={
                    "color": color,
                    "width": 2.5,
                    "shape": "spline",
                    "smoothing": 0.4,
                },
                marker={
                    "size": 8,
                    "symbol": [result["marker"] for result in history],
                    "color": color,
                    "line": {"width": 1, "color": "white"},
                },
                customdata=[
                    [
                        result["meet"],
                        result["date"],
                        result["time"],
                        result["type"],
                    ]
                    for result in history
                ],
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "%{customdata[0]}<br>"
                    "Date: %{customdata[1]}<br>"
                    "Time: %{customdata[2]}<br>"
                    "Meet Type: %{customdata[3]}<extra></extra>"
                ),
            )
        )

    if not figure.data:
        st.info(f"No timed 5K results were found for {selected_year}.")
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
            tickmode="array",
            tickvals=list(range(len(event_order))),
            ticktext=event_labels,
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
    if chart_runner_names:
        st.info(f"No timed 5K results were found for {selected_year}.")
    else:
        st.info("Select at least one athlete to compare.")

st.subheader("Coaches:")
st.caption("To be updated.")

st.subheader("Postseason Results:")
st.caption("To be updated.")

st.subheader("Notes:")
st.caption("To be updated.")
