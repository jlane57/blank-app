import html

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
        margin: 0 0 1.25rem;
        padding: 1.35rem 1.5rem;
        border: 1px solid rgba(25, 57, 84, 0.18);
        border-top: 5px solid #F58220;
        border-radius: 0.75rem;
        background: rgba(255, 248, 239, 0.72);
        box-shadow: 0 4px 14px rgba(16, 42, 67, 0.08);
    }

    .news-date {
        color: #B94E00;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }

    .news-card h2 {
        margin: 0.35rem 0 0.65rem;
        padding: 0;
        border: 0;
        background: transparent;
        font-size: 1.45rem;
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

entries = get_news()
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
        image_html = (
            f'<img src="{html.escape(image.get("display_url", ""))}" '
            f'alt="{html.escape(image.get("alt_text", entry["headline"]))}" '
            'style="width:100%;max-height:420px;object-fit:cover;border-radius:0.5rem;margin-bottom:1rem;">'
            if image.get("display_url")
            else ""
        )
        author = entry.get("author")
        st.markdown(
            (
                '<article class="news-card">'
                f"{image_html}"
                f'<div class="news-date">{html.escape(entry["published"])}</div>'
                f'<h2>{html.escape(entry["headline"])}</h2>'
                f'<p>{html.escape(author) if author else ""}</p>'
                f'<p>{html.escape(entry["body"])}</p>'
                "</article>"
            ),
            unsafe_allow_html=True,
        )
        if selected_index is None and st.button(
            "Read article",
            key=f"read_news_{index}",
            width="stretch",
        ):
            st.session_state.selected_news = index
            st.rerun()
