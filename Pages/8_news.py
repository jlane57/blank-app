import html
from pathlib import Path

import requests
import streamlit as st

from gallery import get_gallery_entries
from news import get_news
from site_status import stop_if_site_offline

stop_if_site_offline()

st.markdown(
    """
    <style>
    .news-kicker {
        color: #B94E00;
        font-size: 0.8rem;
        font-weight: 800;
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }

    .news-intro {
        margin: 0 0 1.5rem;
        color: rgba(16, 42, 67, 0.76);
        font-size: 1.05rem;
    }

    .news-card {
        margin: 0 0 0.75rem;
        padding: 0.25rem 0;
    }

    .news-date {
        color: #B94E00;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .news-card h2,
    .news-card h3 {
        margin: 0.2rem 0 0;
        padding: 0;
        border: 0;
        background: transparent;
        font-size: 1.1rem;
    }

    .news-card p {
        margin: 0;
        color: #193954;
        line-height: 1.65;
        white-space: pre-wrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="news-kicker">Team updates</div>', unsafe_allow_html=True)
st.title("News")
st.markdown(
    '<p class="news-intro">The latest updates, announcements, and team notes.</p>',
    unsafe_allow_html=True,
)

try:
    entries = get_news()
except (OSError, ValueError, RuntimeError, requests.RequestException):
    entries = []
    st.info("News is temporarily unavailable.")
if not entries:
    st.info("No news has been posted yet. Check back soon.")
else:
    selected_index = st.session_state.get("selected_news")
    if selected_index is not None and (
        not isinstance(selected_index, int)
        or selected_index < 0
        or selected_index >= len(entries)
    ):
        st.session_state.selected_news = None
        st.rerun()

    if selected_index is not None:
        if st.button("← Back to News"):
            st.session_state.selected_news = None
            st.rerun()
        visible_entries = [entries[selected_index]]
    else:
        visible_entries = entries

    for index, entry in enumerate(visible_entries):
        image = entry.get("image") or {}
        image_source = image.get("display_url") or image.get("thumbnail_url")
        if not image_source and image.get("file_id"):
            image_source = (
                "https://drive.google.com/thumbnail"
                f"?id={image['file_id']}&sz=w160"
            )
        thumbnail_source = image_source or str(
            Path(__file__).resolve().parents[1] / "Images" / "raiders_athletics_seal.jpeg"
        )
        image_alt = image.get("alt_text") or entry["headline"]

        if selected_index is None:
            with st.container(border=True):
                image_column, content_column = st.columns(
                    [1.25, 5],
                    gap="medium",
                    vertical_alignment="center",
                )
                with image_column:
                    st.image(thumbnail_source, caption=None, width=110)
                with content_column:
                    st.markdown(
                        (
                            '<div class="news-card">'
                            f'<div class="news-date">{html.escape(entry["published"])}</div>'
                            f'<h3>{html.escape(entry["headline"])}</h3>'
                            "</div>"
                        ),
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Read article",
                        key=f"read_news_{index}",
                    ):
                        st.session_state.selected_news = index
                        st.rerun()
            continue

        st.markdown('<article class="news-card">', unsafe_allow_html=True)
        st.markdown(
            (
                f'<div class="news-date">{html.escape(entry["published"])}</div>'
                f'<h2>{html.escape(entry["headline"])}</h2>'
            ),
            unsafe_allow_html=True,
        )
        if image_source:
            image_column, _ = st.columns([1, 1])
            with image_column:
                st.image(image_source, caption=image_alt, use_container_width=True)
        if entry.get("author"):
            st.caption(entry["author"])
        st.markdown(
            f'<p>{html.escape(entry["body"])}</p>',
            unsafe_allow_html=True,
        )
        st.markdown("</article>", unsafe_allow_html=True)
