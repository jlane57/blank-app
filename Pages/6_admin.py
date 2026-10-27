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
    get_optional_spreadsheet_id,
    get_required_secret,
)
from spreadsheet_data import parse_workbook_years
from spreadsheet_data import parse_race_time
from meet_registry import assign_meet_ids

from site_status import (
    DEFAULT_BANNER_MESSAGE,
    get_site_status,
    save_site_status,
)
from spreadsheet_storage import storage_configured
from workbook_source import load_workbook_bytes

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

    [data-testid="stForm"] input,
    [data-testid="stForm"] textarea,
    [data-testid="stForm"] [data-baseweb="select"] > div {
        border: 1px solid rgba(25, 57, 84, 0.4);
        border-radius: 0.45rem;
    }

    [data-testid="stForm"] input:focus,
    [data-testid="stForm"] textarea:focus,
    [data-testid="stForm"] [data-baseweb="select"] > div:focus-within {
        border-color: #F58220;
        box-shadow: 0 0 0 1px #F58220;
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

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "news_authenticated" not in st.session_state:
    st.session_state.news_authenticated = False

st.title(
    "News Portal"
    if st.session_state.news_authenticated and not st.session_state.authenticated
    else "Admin Portal"
)
st.markdown(
    '<p class="admin-intro">Manage site availability, photos, and reviewed meet imports.</p>'
    if not st.session_state.news_authenticated or st.session_state.authenticated
    else '<p class="admin-intro">Publish and manage team news.</p>',
    unsafe_allow_html=True,
)


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


def check_news_password():
    with st.form("news_management_login"):
        password = st.text_input("News management password", type="password")
        submitted = st.form_submit_button("Sign In")

    if submitted:
        configured_password = get_required_secret("NEWS_ADMIN_PASSWORD").strip()
        if len(configured_password) >= 2 and configured_password[0] == configured_password[-1] == '"':
            configured_password = configured_password[1:-1]
        if not configured_password:
            st.error("NEWS_ADMIN_PASSWORD must contain a non-empty password.")
            st.stop()
        if password == configured_password:
            st.session_state.news_authenticated = True
            st.rerun()
        elif password in {"67", "6767"}:
            st.info("Heehee six seven. Still not the password though, nice try")
        else:
            st.error("Access denied")


def render_news_management():
    if "news_view" not in st.session_state:
        st.session_state.news_view = "home"
    if "news_flash" in st.session_state:
        st.success(st.session_state.pop("news_flash"))

    current_news = get_news()
    if st.session_state.news_view == "home":
        if st.button("← Sign out and exit", key="lock_news_management"):
            st.session_state.news_authenticated = False
            st.session_state.news_view = "home"
            st.rerun()
        st.subheader("News Management")
        st.caption("Publish or review updates that appear on the public News page.")
        action_columns = st.columns(2)
        with action_columns[0]:
            if st.button("Write new article", use_container_width=True):
                st.session_state.news_view = "new"
                st.rerun()
        with action_columns[1]:
            if st.button("Review previous articles", use_container_width=True):
                st.session_state.news_view = "review"
                st.rerun()
        return

    try:
        news_meet_options = [("No meet", "")]
        news_meet_options.extend(
            load_image_destinations(get_optional_spreadsheet_id())[0]
        )
    except (OSError, RuntimeError, ValueError, KeyError, requests.RequestException):
        news_meet_options = [("No meet", "")]
    if st.button("← Back to News Management", key="back_to_news_home"):
        st.session_state.news_view = "home"
        st.rerun()

    if st.session_state.news_view == "new":
        st.subheader("Write New Article")
        with st.form("publish_news"):
            news_headline = st.text_input("Header", max_chars=160)
            news_author = st.text_input("Author", max_chars=160, placeholder="Optional")
            news_body = st.text_area("Story", max_chars=5000, height=140)
            news_date = st.date_input("Published date", value=date.today())
            news_image = st.file_uploader(
                "Article image (optional)",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=False,
                help="Drag an image here or click Browse files. Leave blank for no image.",
            )
            news_meet_label = st.selectbox(
                "Tag to a meet (optional)",
                [label for label, _ in news_meet_options],
            )
            publish_news = st.form_submit_button("Publish News")
        if publish_news:
            try:
                image = None
                if news_image is not None:
                    image = upload_image(
                        news_image.getvalue(),
                        news_image.name,
                        caption=news_headline,
                        alt_text=news_headline,
                        category="news",
                    )
                add_news(
                    news_headline,
                    news_body,
                    news_date.isoformat(),
                    image,
                    news_author,
                    dict(news_meet_options)[news_meet_label],
                )
                st.session_state.news_flash = "Article published!"
                st.session_state.news_view = "home"
                st.rerun()
            except (ValueError, OSError, RuntimeError, requests.RequestException) as error:
                st.error(str(error))
        return

    st.subheader("Review Previous Articles")
    if current_news:
        st.caption(f"{len(current_news)} published item(s)")
        for index, entry in enumerate(current_news):
            with st.expander(f"{entry['headline']} · {entry['published']}"):
                current_image = entry.get("image") or {}
                current_image_source = (
                    current_image.get("display_url")
                    or current_image.get("thumbnail_url")
                )
                if not current_image_source and current_image.get("file_id"):
                    current_image_source = (
                        "https://drive.google.com/thumbnail"
                        f"?id={current_image['file_id']}&sz=w600"
                    )
                if current_image_source:
                    st.image(current_image_source, width=180)
                try:
                    current_news_date = date.fromisoformat(entry["published"])
                except ValueError:
                    current_news_date = date.today()
                with st.form(f"edit_news_{index}"):
                    edited_headline = st.text_input(
                        "Header",
                        value=entry["headline"],
                        max_chars=160,
                    )
                    edited_author = st.text_input(
                        "Author",
                        value=entry.get("author", ""),
                        max_chars=160,
                    )
                    edited_body = st.text_area(
                        "Story",
                        value=entry["body"],
                        max_chars=5000,
                        height=140,
                    )
                    edited_date = st.date_input(
                        "Published date",
                        value=current_news_date,
                    )
                    edited_image = st.file_uploader(
                        "Article image (optional)",
                        type=["jpg", "jpeg", "png", "webp"],
                        accept_multiple_files=False,
                        help="Upload a replacement image or leave blank to keep the current image.",
                    )
                    edited_meet_label = st.selectbox(
                        "Tag to a meet (optional)",
                        [label for label, _ in news_meet_options],
                        index=next(
                            (
                                meet_index
                                for meet_index, (_, meet_id) in enumerate(news_meet_options)
                                if meet_id == entry.get("meet_id", "")
                            ),
                            0,
                        ),
                    )
                    save_edit = st.form_submit_button("Save Changes")
                if save_edit:
                    try:
                        edited_image_value = entry.get("image")
                        if edited_image is not None:
                            edited_image_value = upload_image(
                                edited_image.getvalue(),
                                edited_image.name,
                                caption=edited_headline,
                                alt_text=edited_headline,
                                category="news",
                            )
                        edited_entry = {
                            **entry,
                            "headline": edited_headline,
                            "author": edited_author,
                            "body": edited_body,
                            "published": edited_date.isoformat(),
                            "image": edited_image_value,
                            "meet_id": dict(news_meet_options)[edited_meet_label],
                        }
                        save_news(
                            current_news[:index]
                            + [edited_entry]
                            + current_news[index + 1 :],
                            allow_delete=True,
                        )
                        st.session_state.news_flash = "Article published!"
                        st.session_state.news_view = "home"
                        st.rerun()
                    except (
                        ValueError,
                        OSError,
                        RuntimeError,
                        requests.RequestException,
                    ) as error:
                        st.error(str(error))
                if st.button("Delete", key=f"delete_news_{index}"):
                    st.session_state.news_delete_index = index
                    st.rerun()
                if st.session_state.get("news_delete_index") == index:
                    st.warning("Are you sure? This action is permanent!")
                    confirm_columns = st.columns(2)
                    with confirm_columns[0]:
                        if st.button("Confirm delete", key=f"confirm_delete_news_{index}"):
                            save_news(
                                current_news[:index] + current_news[index + 1 :],
                                allow_delete=True,
                            )
                            st.session_state.news_delete_index = None
                            st.session_state.news_view = "home"
                            st.session_state.news_flash = (
                                f'"{entry["headline"]}" has been deleted'
                            )
                            st.rerun()
                    with confirm_columns[1]:
                        if st.button("Cancel", key=f"cancel_delete_news_{index}"):
                            st.session_state.news_delete_index = None
                            st.rerun()
    else:
        st.info("No news items have been published.")


@st.cache_data(ttl=3600)
def load_image_destinations(spreadsheet_id):
    workbook = parse_workbook_years(load_workbook_bytes(spreadsheet_id))["years"]
    meets = []
    athletes = {}
    for year, season in workbook.items():
        assign_meet_ids(season["meets"])
        for meet in season["meets"]:
            meets.append(
                (
                    f"{meet['name']} ({year})",
                    meet["meet_id"],
                )
            )
        for athlete in season["athletes"]:
            key = athlete["name"].casefold()
            athletes[key] = athlete["name"]
    return sorted(meets), sorted(
        ((name, f"athlete:{key}") for key, name in athletes.items()),
        key=lambda item: item[0].casefold(),
    )


if not st.session_state.authenticated and not st.session_state.news_authenticated:
    login_columns = st.columns(2)
    with login_columns[0]:
        st.markdown("#### Admin Portal")
        st.caption("Website settings, imports, photos, and other administrative tools.")
        check_password()
    with login_columns[1]:
        st.markdown("#### News Portal")
        st.caption("Publish and manage news without opening the traditional admin tools.")
        check_news_password()
elif st.session_state.news_authenticated and not st.session_state.authenticated:
    render_news_management()
else:
    st.markdown(
        '<div class="admin-status">● Signed in · Admin access active</div>',
        unsafe_allow_html=True,
    )
    if st.button("Sign Out", key="admin_sign_out"):
        st.session_state.authenticated = False
        st.session_state.news_authenticated = False
        st.rerun()

    section_labels = {
        "availability": "Website Availability",
        "photos": "Photo Uploads",
        "imports": "Import Meet Results",
    }
    if st.session_state.get("admin_section") not in section_labels:
        st.session_state.admin_section = "availability"

    st.subheader("Admin Tools")
    section_columns = st.columns(len(section_labels))
    for column, (section_key, section_label) in zip(
        section_columns, section_labels.items()
    ):
        with column:
            button_label = (
                f"Open {section_label}"
                if st.session_state.admin_section != section_key
                else f"Viewing {section_label}"
            )
            if st.button(
                button_label,
                key=f"open_admin_{section_key}",
                disabled=st.session_state.admin_section == section_key,
                use_container_width=True,
            ):
                st.session_state.admin_section = section_key
                st.rerun()

    st.divider()
    current = get_site_status()

    with st.expander(
        "Website Availability",
        expanded=st.session_state.admin_section == "availability",
    ):
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

    with st.expander(
        "Photo Uploads",
        expanded=st.session_state.admin_section == "photos",
    ):
        st.subheader("Photo Uploads")
        try:
            storage_enabled = storage_configured()
        except (ValueError, RuntimeError):
            storage_enabled = False
        if not storage_enabled:
            st.info(
                "Photo uploads are disabled for the first deployment. "
                "Configure the Google service account and Drive folder before enabling them."
            )
        else:
            st.caption("Choose exactly where each uploaded image should appear.")
        try:
            meet_destinations, athlete_destinations = load_image_destinations(
                get_optional_spreadsheet_id()
            ) if storage_enabled else ([], [])
        except (OSError, ValueError, KeyError, requests.RequestException):
            meet_destinations, athlete_destinations = [], []
        with st.form("photo_upload") if storage_enabled else st.container():
            photo = st.file_uploader(
                "Image files",
                type=["jpg", "jpeg", "png", "webp", "gif"],
                accept_multiple_files=True,
                key="gallery_photo",
            )
            photo_category = st.selectbox(
                "Use image for",
                ["Home page", "Specific meet", "Specific athlete"],
                key="gallery_category",
            )
            destination_options = [("Home page", "home")]
            if photo_category == "Specific meet":
                destination_options = meet_destinations
            elif photo_category == "Specific athlete":
                destination_options = athlete_destinations
            if destination_options:
                destination_labels = [label for label, _ in destination_options]
                destination_label = st.selectbox(
                    "Choose the destination",
                    destination_labels,
                    key="gallery_destination",
                )
                destination_key = dict(destination_options)[destination_label]
            else:
                destination_key = ""
                st.warning("No destinations are currently available.")
            photo_caption = st.text_input("Caption (optional)", key="gallery_caption")
            photo_credit = st.text_input(
                "Photographer credit (optional)",
                key="gallery_credit",
            )
            photo_alt = st.text_input("Accessibility description (optional)", key="gallery_alt")
            photo_featured = st.checkbox(
                "Feature on the home page",
                disabled=photo_category != "Home page",
                key="gallery_featured",
            )
            upload_submitted = st.form_submit_button("Upload Image") if storage_enabled else False
        if upload_submitted:
            if not photo:
                st.error("Choose an image first.")
            elif not destination_key:
                st.error("Choose a valid destination first.")
            else:
                try:
                    category = {
                        "Home page": "Home",
                        "Specific meet": "Meet",
                        "Specific athlete": "Athlete",
                    }[photo_category]
                    for uploaded_photo in photo:
                        upload_image(
                            uploaded_photo.getvalue(),
                            uploaded_photo.name,
                            photo_caption,
                            photo_credit,
                            photo_alt,
                            category,
                            destination_key,
                            photo_featured,
                        )
                    st.success(f"{len(photo)} image(s) uploaded and assigned.")
                    st.rerun()
                except (OSError, ValueError, RuntimeError, requests.RequestException) as error:
                    st.error(f"Could not upload image: {format_spreadsheet_error(error)}")

    with st.expander(
        "Import Meet Results",
        expanded=st.session_state.admin_section == "imports",
    ):
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
                workbook_data = load_workbook_bytes(get_optional_spreadsheet_id())
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