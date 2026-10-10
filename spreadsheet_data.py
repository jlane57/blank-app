import math
import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from io import BytesIO
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

import openpyxl
from openpyxl.utils.datetime import from_excel

PLACEHOLDERS = {"", "n/a", "na", "---", "--", "-", "—", "–", "dnr", "dnf", "dq"}
MEET_COLUMNS = range(3, 26)


def display_text(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, timedelta):
        return format_race_time(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        if value.is_integer():
            return str(int(value))
    return str(value).strip()


def parse_race_time(value):
    if isinstance(value, timedelta):
        return (
            Decimal(value.days * 86400 + value.seconds)
            + Decimal(value.microseconds) / Decimal(1_000_000)
        )
    if isinstance(value, time):
        return (
            Decimal(value.hour * 3600 + value.minute * 60 + value.second)
            + Decimal(value.microsecond) / Decimal(1_000_000)
        )
    if isinstance(value, (bool, int, float, Decimal)) or value is None:
        return None

    text = display_text(value)
    if not text or text.casefold() in PLACEHOLDERS:
        return None

    day_match = re.fullmatch(r"(\d+)\s+days?,?\s+(.+)", text, re.IGNORECASE)
    days = int(day_match.group(1)) if day_match else 0
    if day_match:
        text = day_match.group(2).strip()

    parts = text.split(":")
    if len(parts) in (2, 3):
        try:
            seconds = Decimal(parts[-1])
            if not seconds.is_finite() or not 0 <= seconds < 60:
                return None

            if len(parts) == 2:
                minutes = int(parts[0])
                if minutes < 0:
                    return None
                return Decimal(days * 86400 + minutes * 60) + seconds

            hours, minutes = int(parts[0]), int(parts[1])
            if hours < 0 or not 0 <= minutes < 60:
                return None
            return Decimal(days * 86400 + hours * 3600 + minutes * 60) + seconds
        except (InvalidOperation, ValueError):
            return None

    return None


def format_race_time(value):
    seconds = parse_race_time(value)
    if seconds is None:
        return display_text(value)

    seconds = seconds.quantize(Decimal("0.001"))
    whole_seconds = int(seconds)
    minutes, remainder = divmod(whole_seconds, 60)
    fraction = seconds - Decimal(whole_seconds)
    result = f"{minutes:02d}:{remainder:02d}"
    if fraction:
        result += "." + f"{fraction:.3f}".split(".", 1)[1].rstrip("0")
    return result


def format_grade(value):
    text = display_text(value)
    match = re.fullmatch(r"([+-]?\d+)\.0+", text)
    return match.group(1) if match else text


def format_meet_date(value):
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return f"{value:%B} {value.day}"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            value = from_excel(value)
        except (TypeError, ValueError, OverflowError):
            return display_text(value)
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return f"{value:%B} {value.day}"

    text = display_text(value)
    try:
        parsed = date.fromisoformat(text)
    except ValueError:
        return text
    return f"{parsed:%B} {parsed.day}"


def parse_meet_date(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            converted = from_excel(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if isinstance(converted, datetime):
            return converted.date()
        if isinstance(converted, date):
            return converted

    text = display_text(value)
    for date_format in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(text, date_format).date()
        except ValueError:
            continue
    return None


def sort_meets_by_date(meets):
    def date_key(meet):
        meet_date = parse_meet_date(meet.get("raw_date"))
        return meet_date is None, meet_date or date.max

    return sorted(meets, key=date_key)


def build_athlete_5k_chart_data(results):
    chart_results = [
        result
        for result in results
        if "5k" in str(result.get("type", "")).casefold()
        and result.get("seconds") is not None
    ]
    chart_results.sort(
        key=lambda result: (
            parse_meet_date(result.get("raw_date")) is None,
            parse_meet_date(result.get("raw_date")) or date.max,
            result["year"],
            result["meet"].casefold(),
        )
    )

    if not chart_results:
        return []

    current_pr = min(result["seconds"] for result in chart_results)
    best_so_far = None
    chart_data = []
    for result in chart_results:
        seconds = result["seconds"]
        is_current_pr = seconds == current_pr
        is_record_at_point = best_so_far is None or seconds < best_so_far
        marker = "star" if is_current_pr else "square" if is_record_at_point else "circle"
        best_so_far = seconds if best_so_far is None else min(best_so_far, seconds)
        chart_data.append(
            {
                "name": result["name"],
                "year": str(result["year"]),
                "meet": result["meet"],
                "type": result["type"],
                "date": result["date"],
                "raw_date": result.get("raw_date"),
                "event": f"{result['meet']} ({result['date']}, {result['year']})",
                "seconds": float(seconds),
                "time": result["result"],
                "marker": marker,
            }
        )

    return chart_data


def build_postseason_season_chart_data(years, selected_year):
    season = years[selected_year]
    postseason_athletes = [
        athlete
        for athlete in season["athletes"]
        if athlete.get("is_postseason", False)
    ]
    postseason_names = {athlete["name"].casefold() for athlete in postseason_athletes}
    histories = {name: [] for name in postseason_names}

    for year_data in years.values():
        for athlete in year_data.get("athletes", []):
            name = athlete["name"].casefold()
            if name in histories:
                histories[name].extend(athlete["results"])

    season_results = []
    for athlete in postseason_athletes:
        name = athlete["name"].casefold()
        for result in build_athlete_5k_chart_data(histories[name]):
            if result["year"] != str(selected_year):
                continue
            season_results.append(
                {
                    **result,
                    "athlete": athlete["name"],
                }
            )

    return sorted(
        season_results,
        key=lambda result: (
            parse_meet_date(result["raw_date"]) is None,
            parse_meet_date(result["raw_date"]) or date.max,
            result["event"].casefold(),
            result["athlete"].casefold(),
        ),
    )


def build_race_totals(years):
    results = [
        result
        for season in years.values()
        for result in season.get("results", [])
    ]
    total_seconds = sum(
        (result["seconds"] for result in results),
        start=Decimal(0),
    )
    dated_seasons = [
        meet_date.year
        for season in years.values()
        for meet in season.get("meets", [])
        if (meet_date := parse_meet_date(meet.get("raw_date"))) is not None
    ]
    first_year = min(dated_seasons, default=min(years, default=None))

    return {
        "race_count": len(results),
        "hours_raced": (total_seconds / Decimal(3600)).quantize(
            Decimal("0.1"),
            rounding=ROUND_HALF_UP,
        ),
        "first_year": first_year,
    }


def _format_seconds(seconds):
    seconds = abs(seconds).quantize(Decimal("0.001"))
    whole_seconds = int(seconds)
    minutes, remainder = divmod(whole_seconds, 60)
    result = f"{minutes:02d}:{remainder:02d}"
    fraction = seconds - Decimal(whole_seconds)
    if fraction:
        result += "." + f"{fraction:.3f}".split(".", 1)[1].rstrip("0")
    return result


def build_postseason_roster(years, selected_year):
    season = years[selected_year]
    previous_season = years.get(selected_year - 1, {})

    def personal_record(athlete):
        five_k_results = [
            result
            for result in athlete["results"]
            if result["is_5k"] and result["seconds"] is not None
        ]
        return (
            min(five_k_results, key=lambda result: result["seconds"])
            if five_k_results
            else None
        )

    previous_records = {}
    for athlete in previous_season.get("athletes", []):
        record = personal_record(athlete)
        if record is not None:
            key = athlete["name"].casefold()
            if (
                key not in previous_records
                or record["seconds"] < previous_records[key]["seconds"]
            ):
                previous_records[key] = record

    roster = []
    for athlete in season["athletes"]:
        if not athlete.get("is_postseason", False):
            continue

        record = personal_record(athlete)
        previous_record = previous_records.get(athlete["name"].casefold())
        improvement = "—"
        if record is not None and previous_record is not None:
            change = previous_record["seconds"] - record["seconds"]
            if change > 0:
                improvement = f"-{_format_seconds(change)}"
            elif change < 0:
                improvement = f"+{_format_seconds(change)}"
            else:
                improvement = "00:00"

        roster.append(
            {
                "Athlete": athlete["name"],
                "Grade": athlete["grade"],
                "PR": record["result"] if record else "—",
                "Meet": record["meet"] if record else "—",
                "Improvement": improvement,
                "_seconds": record["seconds"] if record else None,
            }
        )

    roster.sort(
        key=lambda athlete: (
            athlete["_seconds"] is None,
            athlete["_seconds"] if athlete["_seconds"] is not None else Decimal("Infinity"),
            athlete["Athlete"].casefold(),
        )
    )
    previous_seconds = None
    current_rank = 0
    for index, athlete in enumerate(roster, start=1):
        seconds = athlete["_seconds"]
        if seconds is None:
            athlete["Rank"] = "—"
        else:
            if seconds != previous_seconds:
                current_rank = index
            athlete["Rank"] = current_rank
            previous_seconds = seconds
        del athlete["_seconds"]

    return roster


def find_year_sheet_layout(rows):
    """Find the athlete header and metadata rows in either supported layout."""
    header_row = next(
        (
            index
            for index, row in enumerate(rows)
            if len(row) > 1
            and display_text(row[0]).strip().casefold() == "name"
            and display_text(row[1]).strip().casefold() == "grade"
        ),
        None,
    )
    if header_row is None:
        return None

    metadata_labels = {
        "meet type": "meet_type_row",
        "type": "meet_type_row",
        "meet location": "location_row",
        "location": "location_row",
        "meet date": "date_row",
        "date": "date_row",
        "meet notes": "notes_row",
        "notes": "notes_row",
        "team place": "team_place_row",
    }

    def labels_in(rows_to_check):
        labels = {}
        for row_index in rows_to_check:
            for column_index in range(3):
                label = display_text(row_value(rows, row_index, column_index))
                label = re.sub(r"\s*[>:]+\s*$", "", label).strip().casefold()
                if label in metadata_labels:
                    labels[metadata_labels[label]] = row_index
                    break
        return labels

    preceding_rows = range(max(0, header_row - 5), header_row)
    following_rows = range(header_row + 1, min(len(rows), header_row + 6))
    preceding_labels = labels_in(preceding_rows)
    following_labels = labels_in(following_rows)
    metadata_above = len(preceding_labels) > len(following_labels)
    metadata_labels_found = preceding_labels if metadata_above else following_labels
    fallback_offset = -5 if metadata_above else 1

    return {
        "header_row": header_row,
        "meet_type_row": metadata_labels_found.get(
            "meet_type_row", header_row + fallback_offset
        ),
        "location_row": metadata_labels_found.get(
            "location_row", header_row + fallback_offset + 1
        ),
        "date_row": metadata_labels_found.get(
            "date_row", header_row + fallback_offset + 2
        ),
        "notes_row": metadata_labels_found.get(
            "notes_row", header_row + fallback_offset + 3
        ),
        "team_place_row": metadata_labels_found.get(
            "team_place_row", header_row + fallback_offset + 4
        ),
        "first_athlete_row": (
            header_row + 1 if metadata_above else header_row + 6
        ),
    }


def row_value(rows, row_index, column_index):
    if row_index is None or row_index < 0 or row_index >= len(rows):
        return None
    row = rows[row_index]
    if column_index < 0 or column_index >= len(row):
        return None
    return row[column_index]


def parse_year_sheet(rows, year, bold_cells=None):
    """Return typed, calculation-ready records from a supported year tab."""
    layout = find_year_sheet_layout(rows)
    if layout is None:
        return None

    meet_columns = [
        column
        for column in MEET_COLUMNS
        if display_text(row_value(rows, layout["header_row"], column)).strip()
    ]
    meets = []
    for column in meet_columns:
        meets.append(
            {
                "year": year,
                "column": column,
                "name": display_text(row_value(rows, layout["header_row"], column)),
                "raw_type": row_value(rows, layout["meet_type_row"], column),
                "type": display_text(row_value(rows, layout["meet_type_row"], column)),
                "raw_location": row_value(rows, layout["location_row"], column),
                "location": display_text(row_value(rows, layout["location_row"], column)),
                "raw_date": row_value(rows, layout["date_row"], column),
                "date": format_meet_date(row_value(rows, layout["date_row"], column)),
                "raw_notes": row_value(rows, layout["notes_row"], column),
                "notes": display_text(row_value(rows, layout["notes_row"], column)),
                "raw_team_place": row_value(rows, layout["team_place_row"], column),
                "team_place": display_text(row_value(rows, layout["team_place_row"], column)),
            }
        )

    meet_by_column = {meet["column"]: meet for meet in meets}
    athletes = []
    results = []
    for row_index in range(layout["first_athlete_row"], len(rows)):
        raw_name = row_value(rows, row_index, 0)
        name = display_text(raw_name)
        if not name:
            continue

        raw_grade = row_value(rows, row_index, 1)
        athlete = {
            "year": year,
            "row": row_index,
            "raw_name": raw_name,
            "name": name,
            "raw_grade": raw_grade,
            "grade": format_grade(raw_grade),
            "raw_best": row_value(rows, row_index, 2),
            "best": format_race_time(row_value(rows, row_index, 2)),
            "is_postseason": (
                bold_cells is not None and (row_index, 0) in bold_cells
            ),
            "results": [],
        }
        for column in meet_columns:
            raw_result = row_value(rows, row_index, column)
            seconds = parse_race_time(raw_result)
            if seconds is None:
                continue

            meet = meet_by_column[column]
            result = {
                "year": year,
                "row": row_index,
                "column": column,
                "name": name,
                "grade": athlete["grade"],
                "meet": meet["name"],
                "type": meet["type"],
                "location": meet["location"],
                "raw_date": meet["raw_date"],
                "date": meet["date"],
                "team_place": meet["team_place"],
                "raw_result": raw_result,
                "result": format_race_time(raw_result),
                "seconds": seconds,
                "is_varsity": (
                    None if bold_cells is None else (row_index, column) in bold_cells
                ),
                "is_5k": bool(
                    re.search(
                        r"(?<!\d)(?:5\s*k|5000(?:\s*(?:m|meter|metre))?)(?!\d)",
                        f"{meet['name']} {meet['type']}",
                        re.IGNORECASE,
                    )
                ),
            }
            athlete["results"].append(result)
            results.append(result)

        athletes.append(athlete)

    return {
        "year": year,
        "layout": layout,
        "meets": meets,
        "athletes": athletes,
        "results": results,
    }


def parse_workbook_years(workbook_data):
    """Load year tabs in the 2026 layout and report tabs that could not be parsed."""
    workbook = openpyxl.load_workbook(
        BytesIO(workbook_data),
        read_only=True,
        data_only=True,
    )
    parsed_years = {}
    issues = []
    try:
        for sheet_name in workbook.sheetnames:
            if not re.fullmatch(r"\d{4}", sheet_name.strip()):
                continue

            year = int(sheet_name.strip())
            try:
                worksheet = workbook[sheet_name]
                rows = []
                bold_cells = set()
                for row_index, worksheet_row in enumerate(worksheet.iter_rows()):
                    values = []
                    for column_index, cell in enumerate(worksheet_row):
                        values.append(cell.value)
                        if cell.value is not None and cell.font and cell.font.bold:
                            bold_cells.add((row_index, column_index))
                    rows.append(values)

                data = parse_year_sheet(rows, year, bold_cells)
                if data is None:
                    issues.append(
                        f"{year}: missing the expected Name/Grade header row"
                    )
                else:
                    parsed_years[year] = data
            except (
                BadZipFile,
                OSError,
                ParseError,
                ValueError,
                TypeError,
                IndexError,
                KeyError,
                OverflowError,
                AttributeError,
            ) as error:
                issues.append(f"{year}: {error}")
    finally:
        workbook.close()

    return {"years": parsed_years, "issues": issues}
