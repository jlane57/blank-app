from io import BytesIO
from zipfile import BadZipFile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from site_status import stop_if_site_offline
from spreadsheet_config import get_spreadsheet_export_url, get_spreadsheet_id
from spreadsheet_data import parse_workbook_years


stop_if_site_offline()

st.markdown(
    """
    <style>
    .interactive-card {
        padding: 1rem 1.15rem;
        margin: 0.6rem 0 1rem;
        border: 2px solid #F58220;
        border-radius: 14px;
        background: linear-gradient(135deg, rgba(255,248,239,.95), rgba(232,241,248,.8));
    }
    .interactive-card h3 { color: #102A43; margin-top: 0; }
    [data-testid="stRadio"] label {
        font-size: 1.15rem;
        font-weight: 800;
    }
    [data-testid="stMultiSelect"] > div > div,
    [data-testid="stSelectbox"] > div > div {
        border: 2px solid #F58220;
        border-radius: 0.65rem;
        background: rgba(255, 248, 239, 0.92);
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=3600)
def load_interactive_data(spreadsheet_id):
    response = requests.get(
        get_spreadsheet_export_url(spreadsheet_id),
        params={"format": "xlsx"},
        timeout=30,
    )
    response.raise_for_status()
    parsed = parse_workbook_years(response.content)
    rows = []
    for year, season in parsed["years"].items():
        meets = {
            (year, meet["column"]): meet
            for meet in season.get("meets", [])
        }
        for result in season.get("results", []):
            meet = meets.get((year, result["column"]), {})
            rows.append(
                {
                    "Year": int(year),
                    "Athlete": result["name"],
                    "Grade": result.get("grade", ""),
                    "Meet": result["meet"],
                    "Type": result.get("type", ""),
                    "Location": result.get("location", ""),
                    "Date": result.get("date", ""),
                    "Raw Date": meet.get("raw_date"),
                    "Time": result["result"],
                    "Seconds": float(result["seconds"]),
                    "Team": result.get("team", ""),
                    "Gender": (
                        "Boys"
                        if str(result.get("team", "")).upper() == "B"
                        else "Girls"
                        if str(result.get("team", "")).upper() == "G"
                        else ""
                    ),
                    "Team Place": result.get("team_place", ""),
                    "Varsity": result.get("is_varsity"),
                    "5K": result.get("is_5k", False),
                }
            )
    return pd.DataFrame(rows), parsed.get("issues", [])


def _format_seconds(seconds):
    if pd.isna(seconds):
        return "—"
    minutes, remainder = divmod(float(seconds), 60)
    formatted = f"{int(minutes):02d}:{remainder:06.3f}".rstrip("0").rstrip(".")
    return formatted


def _format_signed_seconds(seconds):
    sign = "-" if float(seconds) < 0 else "+"
    return f"{sign}{_format_seconds(abs(float(seconds)))}"


def _format_axis_time(seconds):
    whole_seconds = max(0, int(round(float(seconds))))
    minutes, remainder = divmod(whole_seconds, 60)
    return f"{minutes:02d}:{remainder:02d}"


def _time_axis_ticks(values):
    value_range = max(values) - min(values)
    if value_range >= 300:
        interval = 60
    elif value_range >= 150:
        interval = 30
    elif value_range >= 75:
        interval = 15
    else:
        interval = 10
    minimum = int(min(values) // interval) * interval
    maximum = (int(max(values)) // interval + 1) * interval
    tick_values = list(range(minimum, maximum + 1, interval))
    return tick_values, [_format_axis_time(value) for value in tick_values]


def _top_five_average(results):
    return results.nsmallest(5, "Seconds")["Seconds"].mean()


header_columns = st.columns([3, 1])
with header_columns[0]:
    st.title("Data Interactive")
try:
    data, issues = load_interactive_data(get_spreadsheet_id())
except requests.RequestException:
    st.error("Interactive data is temporarily unavailable.")
    st.stop()
except (BadZipFile, InvalidFileException, OSError, TypeError, ValueError, KeyError):
    st.error("Interactive data is temporarily unavailable.")
    st.stop()

for issue in issues:
    st.warning("Some season data could not be loaded.")

if data.empty:
    st.info("No race results are available for comparison yet.")
    st.stop()

if "interactive_gender" not in st.session_state:
    st.session_state.interactive_gender = "Boys"
with header_columns[1]:
    selected_gender = st.radio(
        "Team",
        options=("Boys", "Girls"),
        horizontal=True,
        key="interactive_gender",
        label_visibility="collapsed",
    )

filtered = data[data["Gender"] == selected_gender]
available_years = sorted(data["Year"].unique(), reverse=True)
if "interactive_years" not in st.session_state:
    st.session_state.interactive_years = available_years[:1]
else:
    st.session_state.interactive_years = [
        year
        for year in st.session_state.interactive_years
        if year in available_years
    ]
selected_years = st.multiselect(
    "Seasons",
    available_years,
    key="interactive_years",
)

filtered = (
    filtered[filtered["Year"].isin(selected_years)]
    if selected_years
    else filtered.iloc[0:0]
)
filtered = filtered[filtered["5K"]]

if filtered.empty:
    st.info("No results match the selected filters.")
    st.stop()

view = st.radio(
    "Comparison",
    (
        "Athlete Comparison",
        "Meet Comparison",
        "Year Comparison",
    ),
    horizontal=True,
    key="interactive_comparison",
)

if view == "Athlete Comparison":
    athletes = sorted(filtered["Athlete"].unique(), key=str.casefold)
    selected_athletes = st.multiselect(
        "Add athletes to compare (click the box, then select names)",
        athletes,
        default=[],
        key=f"interactive_athletes_{view}",
    )
    athlete_data = filtered[
        filtered["Athlete"].isin(selected_athletes) & filtered["5K"]
    ]
    if athlete_data.empty:
        st.info("No athletes are selected yet. Use the box above to add one or more.")
    else:
        summary_rows = []
        for athlete, athlete_results in athlete_data.groupby("Athlete"):
            athlete_results = athlete_results.sort_values(
                ["Year", "Raw Date", "Meet"]
            )
            first_time = athlete_results["Seconds"].iloc[0]
            best_time = athlete_results["Seconds"].min()
            summary_rows.append(
                {
                    "Athlete": athlete,
                    "Results": len(athlete_results),
                    "Meets": athlete_results["Meet"].nunique(),
                    "Best": best_time,
                    "Average": athlete_results["Seconds"].mean(),
                    "Range": athlete_results["Seconds"].max()
                    - athlete_results["Seconds"].min(),
                    "Time Improvement": first_time - best_time,
                    "Improvement %": (
                        (first_time - best_time) / first_time * 100
                        if first_time
                        else 0
                    ),
                }
            )
        summary = pd.DataFrame(summary_rows).sort_values(["Best", "Athlete"])
        display_summary = summary.copy()
        display_summary["Best"] = display_summary["Best"].map(_format_seconds)
        display_summary["Average"] = display_summary["Average"].map(_format_seconds)
        display_summary["Range"] = display_summary["Range"].map(_format_seconds)
        display_summary["Time Improvement"] = display_summary[
            "Time Improvement"
        ].map(_format_seconds)
        display_summary["Improvement %"] = display_summary["Improvement %"].map(
            lambda value: f"{value:.2f}%"
        )
        st.subheader("5K performance summary")
        st.dataframe(display_summary, hide_index=True, width="stretch")

        athlete_chart_data = athlete_data.sort_values(
            ["Year", "Raw Date", "Meet", "Athlete"]
        ).copy()
        event_order = (
            athlete_chart_data[["Year", "Raw Date", "Meet"]]
            .drop_duplicates()
            .reset_index(drop=True)
        )
        event_order["Event Position"] = range(len(event_order))
        athlete_chart_data = athlete_chart_data.merge(
            event_order,
            on=["Year", "Raw Date", "Meet"],
            how="left",
        )
        first_times = (
            athlete_chart_data.groupby("Athlete")["Seconds"]
            .first()
            .rename("First 5K")
        )
        athlete_chart_data["First 5K"] = athlete_chart_data["Athlete"].map(
            first_times
        )
        athlete_chart_data["Time Improvement"] = (
            athlete_chart_data["First 5K"] - athlete_chart_data["Seconds"]
        )
        athlete_chart_data["Improvement %"] = (
            athlete_chart_data["Time Improvement"]
            / athlete_chart_data["First 5K"]
            * 100
        )
        athlete_chart_data["Improvement Time"] = athlete_chart_data[
            "Time Improvement"
        ].map(_format_signed_seconds)
        athlete_chart_data["Improvement Percent"] = athlete_chart_data[
            "Improvement %"
        ].map(lambda value: f"{value:+.2f}%")

        if view == "Athlete Comparison":
            if athlete_chart_data.empty:
                st.info("No 5K results were found for the selected athletes.")
            else:
                figure = px.line(
                    athlete_chart_data,
                    x="Event Position",
                    y="Seconds",
                    color="Athlete",
                    markers=True,
                    line_shape="spline",
                    hover_data={
                        "Year": True,
                        "Time": True,
                        "Date": True,
                        "Type": True,
                        "Improvement Time": True,
                        "Improvement Percent": True,
                        "Time Improvement": False,
                        "Improvement %": False,
                        "Seconds": False,
                        "First 5K": False,
                    },
                    color_discrete_sequence=px.colors.qualitative.Bold,
                )
                tick_values, tick_text = _time_axis_ticks(
                    athlete_chart_data["Seconds"]
                )
                figure.update_yaxes(
                    tickmode="array",
                    tickvals=tick_values,
                    ticktext=tick_text,
                    title="5K time (lower is faster)",
                    gridcolor="#D9E2EC",
                )
                figure.update_xaxes(
                    tickmode="array",
                    tickvals=event_order["Event Position"],
                    ticktext=[
                        f"{row.Meet} ({row.Year})"
                        for row in event_order.itertuples()
                    ],
                    tickangle=-35,
                    showgrid=False,
                )
                figure.update_traces(
                    line={"smoothing": 0.5},
                )
                figure.update_layout(
                    height=500,
                    template="plotly_white",
                    paper_bgcolor="#FFF8EF",
                    plot_bgcolor="#F8FBFD",
                    legend_title="Athlete",
                    margin={"t": 25, "r": 20, "b": 100, "l": 25},
                )
                st.plotly_chart(figure, width="stretch")
elif view == "Meet Comparison":
    meets = sorted(filtered["Meet"].unique(), key=str.casefold)
    selected_meets = st.multiselect(
        "Add meets to compare (click the box, then select names)",
        meets,
        default=[],
        key="interactive_meets",
    )
    meet_data = filtered[filtered["Meet"].isin(selected_meets)]
    if meet_data.empty:
        st.info("Choose at least one meet.")
    else:
        summary_rows = []
        for (year, meet), results in meet_data.groupby(["Year", "Meet"]):
            summary_rows.append(
                {
                    "Year": year,
                    "Meet": meet,
                    "Results": len(results),
                    "Athletes": results["Athlete"].nunique(),
                    "Fastest": results["Seconds"].min(),
                    "Average": results["Seconds"].mean(),
                    "Top 5 Average": _top_five_average(results),
                    "Range": results["Seconds"].max() - results["Seconds"].min(),
                    "Minimum": results["Seconds"].min(),
                    "Maximum": results["Seconds"].max(),
                }
            )
        summary = pd.DataFrame(summary_rows).sort_values(
            ["Year", "Meet"], ascending=[False, True]
        )
        display_summary = summary.copy()
        display_summary["Fastest"] = display_summary["Fastest"].map(_format_seconds)
        display_summary["Average"] = display_summary["Average"].map(_format_seconds)
        display_summary["Top 5 Average"] = display_summary["Top 5 Average"].map(
            _format_seconds
        )
        display_summary["Range"] = display_summary["Range"].map(_format_seconds)
        display_summary = display_summary.drop(columns=["Minimum", "Maximum"])
        st.dataframe(display_summary, hide_index=True, width="stretch")

        chart = summary.melt(
            id_vars=["Year", "Meet", "Minimum", "Maximum"],
            value_vars=["Average", "Top 5 Average"],
            var_name="Measure",
            value_name="Seconds",
        )
        chart["Label"] = chart["Seconds"].map(_format_axis_time)
        figure = px.bar(
            chart,
            x="Meet",
            y="Seconds",
            color="Measure",
            pattern_shape="Year",
            text="Label",
            barmode="group",
            color_discrete_sequence=px.colors.qualitative.Bold,
        )
        tick_values, tick_text = _time_axis_ticks(chart["Seconds"])
        figure.update_yaxes(
            tickmode="array",
            tickvals=tick_values,
            ticktext=tick_text,
            title="5K time (lower is faster)",
            gridcolor="#D9E2EC",
        )
        figure.update_traces(
            textposition="outside",
            hovertemplate=(
                "Meet: %{x}<br>Measure: %{fullData.name}"
                "<br>Time: %{text}<extra></extra>"
            ),
        )
        figure.update_layout(
            height=500,
            template="plotly_white",
            paper_bgcolor="#FFF8EF",
            plot_bgcolor="#F8FBFD",
            legend_title="Measure",
            margin={"t": 25, "r": 20, "b": 100, "l": 25},
        )
        st.subheader("Average and top-five average by meet")
        st.plotly_chart(figure, width="stretch")
        range_figure = go.Figure()
        for _, row in summary.iterrows():
            range_figure.add_bar(
                x=[f"{row['Meet']} ({row['Year']})"],
                y=[row["Maximum"] - row["Minimum"]],
                base=[row["Minimum"]],
                name=str(row["Year"]),
                marker_color=px.colors.qualitative.Bold[
                    int(row["Year"]) % len(px.colors.qualitative.Bold)
                ],
                showlegend=False,
                hovertemplate=(
                    f"Meet: {row['Meet']} ({row['Year']})"
                    "<br>Range: %{base}–%{customdata}<extra></extra>"
                ),
                customdata=[row["Maximum"]],
            )
        range_figure.update_yaxes(
            tickmode="array",
            tickvals=_time_axis_ticks(
                summary[["Minimum", "Maximum"]].to_numpy().ravel()
            )[0],
            ticktext=_time_axis_ticks(
                summary[["Minimum", "Maximum"]].to_numpy().ravel()
            )[1],
            title="Result range (lower is faster)",
            gridcolor="#D9E2EC",
        )
        range_figure.update_layout(
            height=450,
            template="plotly_white",
            paper_bgcolor="#FFF8EF",
            plot_bgcolor="#F8FBFD",
            margin={"t": 25, "r": 20, "b": 100, "l": 25},
        )
        st.subheader("Result range by meet")
        st.plotly_chart(range_figure, width="stretch")
        st.caption(
            "The table includes each meet's full result range; top-five averages use "
            "the five fastest recorded results under the active filters."
        )

elif view == "Year Comparison":
    season_summary = (
        filtered.groupby("Year", as_index=False)
        .agg(
            Results=("Seconds", "count"),
            Athletes=("Athlete", "nunique"),
            Meets=("Meet", "nunique"),
            Fastest=("Seconds", "min"),
            Average=("Seconds", "mean"),
            Range=("Seconds", lambda values: values.max() - values.min()),
        )
        .sort_values("Year")
    )
    top_five_by_year = pd.DataFrame(
        [
            {
                "Year": year,
                "Meet": meet,
                "Top 5 Average": _top_five_average(results),
            }
            for (year, meet), results in filtered.groupby(["Year", "Meet"])
        ]
    ).groupby("Year", as_index=False)["Top 5 Average"].mean()
    season_summary = season_summary.merge(
        top_five_by_year, on="Year", how="left"
    )
    display_season_summary = season_summary.copy()
    display_season_summary["Fastest"] = display_season_summary["Fastest"].map(
        _format_seconds
    )
    display_season_summary["Average"] = display_season_summary["Average"].map(
        _format_seconds
    )
    display_season_summary["Top 5 Average"] = display_season_summary[
        "Top 5 Average"
    ].map(_format_seconds)
    display_season_summary["Range"] = display_season_summary["Range"].map(
        _format_seconds
    )
    st.subheader("Year summary")
    st.dataframe(display_season_summary, hide_index=True, width="stretch")

    season_chart = season_summary.rename(
        columns={"Top 5 Average": "Seconds"}
    )[["Year", "Seconds"]]
    figure = px.line(
        season_chart,
        x="Year",
        y="Seconds",
        markers=True,
        line_shape="spline",
        color_discrete_sequence=px.colors.qualitative.Bold,
    )
    tick_values, tick_text = _time_axis_ticks(
        season_chart["Seconds"]
    )
    figure.update_yaxes(
        tickmode="array",
        tickvals=tick_values,
        ticktext=tick_text,
        title="Race time (lower is faster)",
        gridcolor="#D9E2EC",
    )
    figure.update_traces(line={"smoothing": 0.5})
    figure.update_layout(
        height=450,
        template="plotly_white",
        paper_bgcolor="#FFF8EF",
        plot_bgcolor="#F8FBFD",
        margin={"t": 25, "r": 20, "b": 55, "l": 25},
    )
    st.subheader("Top-five average by year")
    st.plotly_chart(figure, width="stretch")
