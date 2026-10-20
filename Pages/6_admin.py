import streamlit as st
import requests
import pandas as pd
from datetime import date
from gallery import get_gallery_entries, upload_image
from meet_import import (
    GROUPS,
    MAX_IMPORT_ROWS,
    SUPPORTED_EXTENSIONS,
    apply_approved_results,
    extract_result_rows,
    extract_rows,
    match_to_roster,
)
from news import add_news, get_news, save_news
from spreadsheet_config import (
    format_spreadsheet_error,
    get_required_secret,
    get_spreadsheet_export_url,
    get_spreadsheet_id,
)
from spreadsheet_data import parse_workbook_years
from spreadsheet_data import parse_race_time

from site_status import (
    DEFAULT_BANNER_MESSAGE,
    get_site_status,
    save_site_status,
)

st.markdown(
    """
    <style>
    .admin-kicker {
        margin: -0.5rem 0 0.35rem;
        color: #B94E00;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.14em;
        text-transform: uppercase;
    }

    .admin-intro {
        margin: 0 0 1.25rem;
        color: rgba(16, 42, 67, 0.78);
        font-size: 1rem;
    }

    .admin-status {
        display: inline-block;
        margin: 0.25rem 0 1rem;
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        background: #E8F1F8;
        color: #102A43;
        font-size: 0.82rem;
        font-weight: 800;
    }

    [data-testid="stForm"] {
        border-color: rgba(25, 57, 84, 0.2);
        border-top: 4px solid #F58220;
        background: rgba(255, 248, 239, 0.5);
    }

    [data-testid="stExpander"] {
        border-color: rgba(25, 57, 84, 0.22);
        background: rgba(232, 241, 248, 0.38);
    }

    div.stButton > button,
    [data-testid="stFormSubmitButton"] button {
        border: 1px solid #F58220;
        background: #F58220;
        color: #102A43;
        font-weight: 800;
    }

    div.stButton > button:hover,
    [data-testid="stFormSubmitButton"] button:hover {
        border-color: #B94E00;
        background: #FFB15C;
        color: #102A43;
    }

    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #102A43;
        border-bottom-color: #F58220;
    }

    [data-testid="stFileUploaderDropzone"] {
        border: 2px dashed rgba(245, 130, 32, 0.65);
        background: rgba(255, 248, 239, 0.55);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="admin-kicker">Restricted workspace</div>', unsafe_allow_html=True)
st.title("Admin Center")
st.markdown(
    '<p class="admin-intro">Manage site availability, announcements, and reviewed meet imports.</p>',
    unsafe_allow_html=True,
)

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
    st.subheader("Sign in to continue")
    st.caption("Admin controls are password protected.")
    check_password()
else:
    st.markdown(
        '<div class="admin-status">● Signed in · Admin access active</div>',
        unsafe_allow_html=True,
    )
    if st.button("Sign Out", key="admin_sign_out"):
        st.session_state.authenticated = False
        st.rerun()

    current = get_site_status()

    with st.container(border=True):
        st.subheader("Website Availability")
        st.caption("Control whether visitors can access the public site.")

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
        st.subheader("News")
        st.caption("Publish updates that appear on the public News page.")
        try:
            news_images = get_gallery_entries()
        except (KeyError, OSError, ValueError, requests.RequestException):
            news_images = []
        with st.form("publish_news"):
            news_headline = st.text_input("Headline", max_chars=160)
            news_body = st.text_area("Story", max_chars=5000, height=140)
            news_date = st.date_input("Published date", value=date.today())
            image_options = {"No image": None}
            image_options.update(
                {
                    f"{entry['caption'] or entry['file_id']} · {entry['date_uploaded']}": entry
                    for entry in news_images
                    if entry["category"].casefold() == "news"
                }
            )
            news_image_label = st.selectbox("Article image", list(image_options))
            publish_news = st.form_submit_button("Publish News")

        if publish_news:
            try:
                add_news(
                    news_headline,
                    news_body,
                    news_date.isoformat(),
                    image_options[news_image_label],
                )
                st.success("News item published.")
                st.rerun()
            except ValueError as error:
                st.error(str(error))

        current_news = get_news()
        if current_news:
            st.caption(f"{len(current_news)} published item(s)")
            for index, entry in enumerate(current_news):
                with st.expander(f"{entry['headline']} · {entry['published']}"):
                    st.write(entry["body"])
                    if st.button("Delete", key=f"delete_news_{index}"):
                        save_news(
                            current_news[:index] + current_news[index + 1 :]
                        )
                        st.success("News item deleted.")
                        st.rerun()
        else:
            st.info("No news items have been published.")

    with st.container(border=True):
        st.subheader("Photo Uploads")
        st.caption("Upload an image to the shared gallery for approved pages to use.")
        with st.form("photo_upload"):
            photo = st.file_uploader(
                "Image file",
                type=["jpg", "jpeg", "png", "webp"],
                key="gallery_photo",
            )
            photo_category = st.selectbox(
                "Use image for",
                ["News", "Meet", "Home"],
                key="gallery_category",
            )
            photo_related_key = st.text_input(
                "Related headline or meet name (optional)",
                key="gallery_related_key",
            )
            photo_caption = st.text_input("Caption (optional)", key="gallery_caption")
            photo_credit = st.text_input(
                "Photographer credit (optional)",
                key="gallery_credit",
            )
            photo_alt = st.text_input("Accessibility description (optional)", key="gallery_alt")
            photo_featured = st.checkbox("Feature on the home page", key="gallery_featured")
            upload_submitted = st.form_submit_button("Upload Image")
        if upload_submitted:
            if not photo:
                st.error("Choose an image first.")
            else:
                try:
                    upload_image(
                        photo.getvalue(),
                        photo.name,
                        photo_caption,
                        photo_credit,
                        photo_alt,
                        photo_category,
                        photo_related_key,
                        photo_featured,
                    )
                    st.success("Image uploaded and added to the gallery.")
                    st.rerun()
                except (OSError, ValueError, requests.RequestException) as error:
                    st.error(f"Could not upload image: {format_spreadsheet_error(error)}")

    with st.container(border=True):
        st.subheader("Import Meet Results")
        st.warning(
            "Imports never write directly to the live records. Review and confirm "
            "the rows, then download the approved file."
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
                st.error(
                    "Could not prepare the import: "
                    f"{format_spreadsheet_error(error)}"
                )

        boys_tab, girls_tab = st.tabs(["Boys import", "Girls import"])
        with boys_tab:
            render_import("B")
        with girls_tab:
            render_import("G")

    if st.button(
        "Refresh Spreadsheet Data Now",
        help="Clear cached data so the next page load fetches fresh information.",
    ):
        st.cache_data.clear()
        st.success(
            "Data cache cleared. The latest sheet data will load when pages are "
            "next opened or refreshed."
        )