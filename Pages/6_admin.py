import streamlit as st
import requests
import pandas as pd
from meet_import import (
    GROUPS,
    MAX_IMPORT_ROWS,
    SUPPORTED_EXTENSIONS,
    apply_approved_results,
    extract_result_rows,
    extract_rows,
    match_to_roster,
)
from spreadsheet_config import get_required_secret, get_spreadsheet_export_url, get_spreadsheet_id
from spreadsheet_data import parse_workbook_years
from spreadsheet_data import parse_race_time

from site_status import (
    DEFAULT_BANNER_MESSAGE,
    get_site_status,
    save_site_status,
)

st.title("Admin Portal")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def check_password():
    with st.form("admin_login"):
        password = st.text_input("Enter Password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        configured_password = get_required_secret("ADMIN_PASSWORD")
        if password == configured_password:
            st.session_state.authenticated = True
            st.rerun()
        elif password in {"67", "6767"}:
            st.info("Heehee six seven. Still not the password though, nice try")
        else:
            st.error("Access denied")


if not st.session_state.authenticated:
    st.subheader("Please Enter the Admin Password")
    check_password()
else:
    st.success("Access granted")
    st.write("Welcome, Admin!")

    current = get_site_status()

    with st.container(border=True):
        st.subheader("Website Availability")

        with st.form("website_availability"):
            enabled = st.toggle(
                "Website Is On",
                value=current["enabled"],
                help="Turn this off to show the custom message on public pages.",
            )
            offline_message = st.text_area(
                "Message Shown While the Website Is Off",
                value=current["offline_message"],
                placeholder="Enter the message visitors should see.",
            )
            banner_enabled = st.toggle(
                "Show Site-Wide Banner",
                value=current["banner_enabled"],
                help="Display the banner message at the top of every page.",
            )
            banner_message = st.text_area(
                "Site-Wide Banner Message",
                value=current["banner_message"],
                placeholder=DEFAULT_BANNER_MESSAGE,
                max_chars=1000,
                help="The banner is saved persistently and shown on every page when enabled.",
            )
            submitted = st.form_submit_button("Save Settings")

        if submitted:
            try:
                save_site_status(
                    enabled,
                    offline_message,
                    banner_enabled,
                    banner_message,
                )
                st.success("Website settings saved.")
            except OSError as error:
                st.error(f"Could not save website settings: {error}")

    with st.container(border=True):
        st.subheader("Import Meet Results")
        st.warning(
            "Imports never write directly to the live Google Sheet. Review and confirm "
            "the rows, then download the approved workbook."
        )
        st.caption(
            "Times are stored as strings in MM:SS[.DDD]. Fractional zeroes are trimmed. "
            "Every value added by an import is italicized."
        )

        def render_import(group):
            uploaded = st.file_uploader(
                f"Upload {GROUPS[group]} results",
                type=[extension.lstrip(".") for extension in SUPPORTED_EXTENSIONS],
                key=f"meet_results_upload_{group}",
            )
            if not uploaded:
                return
            try:
                response = requests.get(
                    get_spreadsheet_export_url(get_spreadsheet_id()),
                    params={"format": "xlsx"},
                    timeout=30,
                )
                response.raise_for_status()
                workbook_data = response.content
                workbook_years = parse_workbook_years(workbook_data)["years"]
                if not workbook_years:
                    raise ValueError("No supported roster year sheets were found.")
                year = st.selectbox("Roster year", sorted(workbook_years, reverse=True), key=f"year_{group}")
                source_rows = extract_rows(uploaded.name, uploaded.getvalue())
                extracted = extract_result_rows(source_rows)
                if len(extracted) > MAX_IMPORT_ROWS:
                    raise ValueError(f"The import exceeds the {MAX_IMPORT_ROWS}-row limit.")
                season = workbook_years[year]
                meets = {meet["name"]: meet for meet in season["meets"]}
                choice = st.selectbox(
                    "Meet column",
                    ["Create a new meet"] + list(meets),
                    key=f"meet_choice_{group}",
                )
                details = {}
                if choice == "Create a new meet":
                    details["name"] = st.text_input("Meet name", key=f"name_{group}")
                    details["race_type"] = st.text_input("Race type", key=f"type_{group}")
                    details["location"] = st.text_input("Location", key=f"location_{group}")
                    details["date"] = st.date_input("Meet date", key=f"date_{group}").isoformat()
                    details["notes"] = st.text_area("Meet notes", key=f"notes_{group}")
                    details["existing_meet"] = ""
                else:
                    details = {"existing_meet": choice, "name": choice}
                    details["team_place"] = st.text_input(
                        f"{GROUPS[group]} place (optional)", key=f"place_{group}"
                    )
                if choice == "Create a new meet":
                    details["team_place"] = st.text_input(
                        f"{GROUPS[group]} place (optional)", key=f"place_{group}"
                    )
                suggestions = match_to_roster(extracted, season["athletes"], group)
                preview = pd.DataFrame(suggestions)

                def confidence_color(value):
                    if value >= 0.9:
                        return "background-color: #C6EFCE; color: #006100"
                    if value >= 0.72:
                        return "background-color: #FFEB9C; color: #9C6500"
                    return "background-color: #FFC7CE; color: #9C0006"

                st.caption(
                    "Confidence preview: green = strong match, yellow = review carefully, "
                    "red = unmatched or low confidence. Edit the table below before approval."
                )
                st.dataframe(
                    preview.style.map(confidence_color, subset=["confidence"]),
                    hide_index=True,
                    column_config={
                        "confidence": st.column_config.NumberColumn(
                            "Confidence", format="%.0f%%"
                        )
                    },
                )
                edited = st.data_editor(
                    suggestions,
                    hide_index=True,
                    num_rows="fixed",
                    disabled=["source_row", "source_name", "confidence", "status", "valid_time"],
                    column_config={
                        "athlete": st.column_config.TextColumn("Roster athlete"),
                        "time": st.column_config.TextColumn("Time (MM:SS[.DDD])"),
                        "confidence": st.column_config.NumberColumn("Confidence", format="%.0f%%"),
                    },
                    key=f"meet_import_review_{group}",
                )
                edited_rows = edited.to_dict("records") if hasattr(edited, "to_dict") else edited
                invalid = []
                for row in edited_rows:
                    row["valid_time"] = bool(parse_race_time(row.get("time")))
                    row["status"] = "Reviewed" if row["valid_time"] and row.get("athlete") else "Needs review"
                    if not row["valid_time"] or not row.get("athlete"):
                        invalid.append(row)
                overwrite = st.checkbox(
                    "Allow replacing existing results (corrections only)",
                    key=f"overwrite_{group}",
                )
                confirmed = st.checkbox(
                    f"I reviewed every {GROUPS[group]} row and approve this import.",
                    key=f"confirmed_{group}",
                )
                if invalid:
                    st.error(f"{len(invalid)} row(s) need correction before export.")
                if st.button(
                    f"Confirm and prepare {GROUPS[group]} workbook",
                    type="primary",
                    key=f"apply_{group}",
                ):
                    if invalid or not confirmed:
                        st.error("Correct all rows and confirm the review before exporting.")
                    else:
                        approved = apply_approved_results(
                            workbook_data, year, group, details, edited_rows, overwrite
                        )
                        st.download_button(
                            "Download approved workbook",
                            approved,
                            file_name=f"meet-results-{year}-{group}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"download_{group}",
                        )
                        st.success("Approved workbook is ready to download.")
            except (requests.RequestException, ValueError, OSError) as error:
                st.error(f"Could not prepare the import: {error}")

        boys_tab, girls_tab = st.tabs(["Boys import", "Girls import"])
        with boys_tab:
            render_import("B")
        with girls_tab:
            render_import("G")

    if st.button(
        "Refresh Spreadsheet Data Now",
        help="Clear Streamlit's cached data so the next page load fetches fresh spreadsheet data.",
    ):
        st.cache_data.clear()
        st.success(
            "Data cache cleared. The latest sheet data will load when pages are "
            "next opened or refreshed."
        )