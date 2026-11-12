"""Guards against layout CSS depending on Streamlit internals that change."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "streamlit_app.py", ROOT / "Pages" / "1_home.py"]


def test_layout_uses_measured_sidebar_state_not_streamlit_attributes():
    for path in FILES:
        text = path.read_text()
        assert "body:has([data-testid=\"stSidebar\"]" not in text, path.name
        assert "> .main" not in text, path.name


def test_sidebar_state_is_synced_by_script():
    text = (ROOT / "streamlit_app.py").read_text()
    assert "data-hxc-sidebar" in text or "hxcSidebar" in text
    for path in FILES:
        assert 'html[data-hxc-sidebar="open"]' in path.read_text() or path.name == "streamlit_app.py"
