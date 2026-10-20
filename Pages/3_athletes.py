import re
from difflib import SequenceMatcher
from datetime import date
from zipfile import BadZipFile

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from openpyxl.utils.exceptions import InvalidFileException

from site_status import stop_if_site_offline
from spreadsheet_config import (
	get_spreadsheet_export_url,
	get_spreadsheet_id,
)
from spreadsheet_data import (
	build_athlete_5k_chart_data,
	parse_meet_date,
	parse_workbook_years,
)
from gallery import get_gallery_entries

stop_if_site_offline()

SPREADSHEET_ID = get_spreadsheet_id()


def class_year(grade, roster_year):
	match = re.search(r"\d+", str(grade))
	if not match:
		return None

	grade_number = int(match.group())
	if not 9 <= grade_number <= 12:
		return None
	return roster_year + 13 - grade_number


def grade_standing(grade):
	match = re.search(r"\d+", str(grade))
	if not match:
		return ""

	return {
		9: "Freshman",
		10: "Sophomore",
		11: "Junior",
		12: "Senior",
	}.get(int(match.group()), "")


def _edit_distance(left, right):
	rows = len(left) + 1
	columns = len(right) + 1
	distance = [[0] * columns for _ in range(rows)]

	for i in range(rows):
		distance[i][0] = i
	for j in range(columns):
		distance[0][j] = j

	for i in range(1, rows):
		for j in range(1, columns):
			cost = 0 if left[i - 1] == right[j - 1] else 1
			distance[i][j] = min(
				distance[i - 1][j] + 1,
				distance[i][j - 1] + 1,
				distance[i - 1][j - 1] + cost,
			)
			if (
				i > 1
				and j > 1
				and left[i - 1] == right[j - 2]
				and left[i - 2] == right[j - 1]
			):
				distance[i][j] = min(
					distance[i][j], distance[i - 2][j - 2] + 1
				)

	return distance[-1][-1]


def _word_match_score(query_word, athlete_word):
	if query_word == athlete_word:
		return 1.0

	if athlete_word.startswith(query_word):
		return 0.82 + 0.16 * len(query_word) / len(athlete_word)
	if len(query_word) < 3 or len(athlete_word) < 3:
		return 0.0
	if query_word in athlete_word:
		return 0.88

	similarity = SequenceMatcher(None, query_word, athlete_word).ratio()
	allowed_edits = max(1, len(query_word) // 3)
	minimum_similarity = 0.66 if len(query_word) <= 4 else 0.55
	if (
		_edit_distance(query_word, athlete_word) <= allowed_edits
		and similarity >= minimum_similarity
	):
		return similarity
	return 0.0


def athlete_match_score(query, athlete, roster_years):
	query = str(query or "").strip().casefold()
	if not query:
		return 1.0

	query_years = [
		int(year) for year in re.findall(r"(?<!\d)\d{4}(?!\d)", query)
	]
	is_class_search = bool(re.search(r"\bclass\b", query))
	if query_years:
		if is_class_search:
			if athlete.get("class_year") not in query_years:
				return None
		elif not any(year in roster_years for year in query_years) and athlete.get("class_year") not in query_years:
			return None

	name_query = re.sub(
		r"\bclass\b|\bof\b|(?<!\d)\d{4}(?!\d)", " ", query
	)
	query_words = re.findall(r"[a-z0-9]+", name_query)
	if not query_words:
		return 1.0 if query_years else None
	if len(query_words) == 1 and len(query_words[0]) == 1 and not query_years:
		return None

	standings = athlete.get("search_standings") or [
		grade_standing(athlete.get("grade", ""))
	]
	searchable_text = " ".join(
		filter(None, [athlete.get("name", ""), *standings])
	).casefold()
	athlete_words = re.findall(r"[a-z0-9]+", searchable_text)
	name_words = re.findall(r"[a-z0-9]+", str(athlete.get("name", "")).casefold())
	scores = [
		max(
			(
				_word_match_score(word, candidate)
				for candidate in (name_words if len(word) <= 2 and len(query_words) > 1 else athlete_words)
			),
			default=0,
		)
		for word in query_words
	]
	if any(score == 0 for score in scores):
		return None

	match_score = sum(scores) / len(scores)
	if query_words == name_words:
		match_score += 0.2
	return match_score


@st.cache_data(ttl=3600)
def load_rosters(spreadsheet_id):
	url = get_spreadsheet_export_url(spreadsheet_id)
	response = requests.get(url, params={"format": "xlsx"}, timeout=30)
	response.raise_for_status()
	workbook_data = parse_workbook_years(response.content)
	rosters = {}
	for year, data in workbook_data["years"].items():
		athletes = data["athletes"]
		for athlete in athletes:
			athlete["class_year"] = class_year(athlete["grade"], year)
		rosters[year] = athletes
	return rosters, workbook_data["issues"]


st.title("Athlete Directory")

try:
	rosters, workbook_issues = load_rosters(SPREADSHEET_ID)
except (
	requests.RequestException,
	BadZipFile,
	OSError,
	KeyError,
	ValueError,
	TypeError,
	OverflowError,
	InvalidFileException,
) as error:
	st.error("Athlete information is temporarily unavailable.")
	st.stop()

for issue in workbook_issues:
	st.warning("Some athlete information could not be loaded.")

years = sorted(rosters, reverse=True)
if not years:
	st.error("No athlete information is available yet.")
	st.stop()

latest_class_year = {}
for year in years:
	for item in rosters[year]:
		name = item["name"].casefold()
		if name not in latest_class_year:
			calculated_class_year = class_year(item["grade"], year)
			if calculated_class_year is not None:
				latest_class_year[name] = calculated_class_year

for year in years:
	for item in rosters[year]:
		item["class_year"] = latest_class_year.get(item["name"].casefold())
	rosters[year].sort(key=lambda item: item["name"].casefold())

directory = {}
for year in years:
	for item in rosters[year]:
		name = item["name"].casefold()
		entry = directory.setdefault(name, {
			"year": year,
			"item": item,
			"roster_years": set(),
			"standings": set(),
		})
		entry["roster_years"].add(year)
		standing = grade_standing(item["grade"])
		if standing:
			entry["standings"].add(standing)

directory_by_year = {year: [] for year in years}
for entry in directory.values():
	directory_by_year[entry["year"]].append(entry)

selected = st.session_state.get("selected_athlete")
if selected:
	if not isinstance(selected, (tuple, list)) or len(selected) not in (2, 3):
		st.session_state.selected_athlete = None
		st.rerun()

	selected_name, selected_class_year = selected[:2]
	selected_team = selected[2] if len(selected) == 3 else ""
	if not isinstance(selected_name, str):
		st.session_state.selected_athlete = None
		st.rerun()
	athlete = next(
		(
			item
			for year in years
			for item in rosters[year]
			if item["name"].casefold() == selected_name
			and item["class_year"] == selected_class_year
			and (not selected_team or item.get("team", "").upper() == selected_team)
		),
		None,
	)
	if athlete is None:
		st.session_state.selected_athlete = None
		st.rerun()

	if st.button("← Back to All Athletes"):
		st.session_state.selected_athlete = None
		st.rerun()

	athlete_results = [
		result
		for year in years
		for roster_athlete in rosters[year]
		if roster_athlete["name"].casefold() == selected_name
		and roster_athlete["class_year"] == selected_class_year
		for result in roster_athlete["results"]
	]
	athlete_results.sort(
		key=lambda result: (
			-result["year"],
			parse_meet_date(result["raw_date"]) is None,
			parse_meet_date(result["raw_date"]) or date.max,
			result["meet"].casefold(),
		)
	)
	five_k_results = [
		result for result in athlete_results
		if result["is_5k"] and result["seconds"] is not None
	]
	if five_k_results:
		personal_record = min(five_k_results, key=lambda result: result["seconds"])
		personal_record_label = personal_record["result"]
	else:
		personal_record_label = "No 5K result"

	team_label = "Girls" if athlete.get("team", "").upper() == "G" else "Boys"
	st.title(athlete["name"])
	st.caption(f"{team_label} Team")
	try:
		athlete_images = [
			image
			for image in get_gallery_entries()
			if image["category"].casefold() == "athlete"
			and image["related_key"] == f"athlete:{selected_name}"
			and image["approved"].casefold() != "false"
		][:6]
	except (KeyError, OSError, ValueError, requests.RequestException):
		athlete_images = []
	if athlete_images:
		image_columns = st.columns(min(3, len(athlete_images)))
		for index, image in enumerate(athlete_images):
			with image_columns[index % len(image_columns)]:
				st.image(
					image["thumbnail_url"] or image["display_url"],
					caption=image["caption"] or None,
					use_container_width=True,
				)
	class_label = f"Class of {athlete['class_year']}" if athlete["class_year"] else "Unknown"
	class_column, pr_column = st.columns(2)
	class_column.metric("Class", class_label)
	pr_column.metric("5K PR", personal_record_label)

	st.subheader("5K Progression")
	chart_results = build_athlete_5k_chart_data(athlete_results)
	if chart_results:
		chart_data = pd.DataFrame(chart_results)
		years_in_chart = sorted(chart_data["year"].unique())
		color_palette = px.colors.qualitative.Dark24
		color_map = {
			year: color_palette[index % len(color_palette)]
			for index, year in enumerate(years_in_chart)
		}
		event_order = chart_data["event"].tolist()
		event_labels = [
			str(meet)[:5]
			for meet in chart_data["meet"]
		]
		tick_interval = 30
		min_seconds = min(chart_data["seconds"])
		max_seconds = max(chart_data["seconds"])
		tick_start = int(min_seconds // tick_interval) * tick_interval
		tick_end = int(max_seconds // tick_interval + 1) * tick_interval
		tick_values = list(range(tick_start, tick_end + 1, tick_interval))
		figure = go.Figure()
		for year in years_in_chart:
			year_data = chart_data[chart_data["year"] == year]
			figure.add_trace(
				go.Scatter(
					x=year_data["event"],
					y=year_data["seconds"],
					mode="lines+markers",
					name=year,
					line={"color": color_map[year], "width": 2, "shape": "spline", "smoothing": 0.4},
					marker={
						"size": 13,
						"symbol": year_data["marker"],
						"line": {"width": 1.5, "color": "white"},
					},
					customdata=year_data[["meet", "date", "time", "type", "year"]],
					hovertemplate=(
						"<b>%{customdata[0]}</b><br>"
						"Date: %{customdata[1]}<br>"
						"Time: %{customdata[2]}<br>"
						"Meet Type: %{customdata[3]}<br>"
						"Season: %{customdata[4]}<extra></extra>"
					),
				)
			)
		figure.update_layout(
			template="plotly_white",
			height=430,
			legend_title_text="Season",
			margin={"t": 25, "r": 20, "b": 100, "l": 25},
			xaxis_title="Meet (Chronological)",
			yaxis_title="5K Time",
		)
		figure.update_xaxes(
			categoryorder="array",
			categoryarray=event_order,
			tickmode="array",
			tickvals=event_order,
			ticktext=event_labels,
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
		st.info("No timed 5K results were found for this athlete.")

	st.subheader("Meet Times")
	if athlete_results:
		for year in sorted({result["year"] for result in athlete_results}, reverse=True):
			st.markdown(f"**{year}**")
			st.dataframe(
				pd.DataFrame(
					[
						{
							"Meet": result["meet"],
							"Type": result["type"],
							"Time": result["result"],
						}
						for result in athlete_results
						if result["year"] == year
					]
				),
				height="content",
				hide_index=True,
				width="stretch",
			)
	else:
		st.info("No meet times were found for this athlete.")
else:
	search = st.text_input(
		"Search Athletes",
		type="search",
		placeholder="Start typing an athlete name…",
		live=True,
	).strip().casefold()

	matches = []
	if search:
		for entry in directory.values():
			item = dict(entry["item"], search_standings=entry["standings"])
			match_score = athlete_match_score(search, item, entry["roster_years"])
			if match_score is not None:
				matches.append((match_score, entry["year"], entry["item"]))
		matches.sort(
			key=lambda match: (
				-match[0],
				-match[1],
				match[2]["name"].casefold(),
			)
		)

	def show_athlete_button(item, key):
		if st.button(item["name"], key=key, width="stretch"):
			st.session_state.selected_athlete = (
				item["name"].casefold(),
				item["class_year"],
				item.get("team", "").upper(),
			)
			st.rerun()

	if search:
		if matches:
			st.caption("Matching Athletes")
			for _, year, item in matches:
				show_athlete_button(item, f"search_{year}_{item['row']}")
		else:
			st.info("No athletes match that search.")

	st.subheader("All Athletes")
	for year in years:
		for team, label in (("B", "Boys"), ("G", "Girls")):
			team_roster = [
				item for item in rosters[year]
				if item.get("team", "").upper() == team
			]
			if not team_roster:
				continue
			st.markdown(f"**{year} {label}**")
			for item in team_roster:
				show_athlete_button(item, f"athlete_{year}_{team}_{item['row']}")