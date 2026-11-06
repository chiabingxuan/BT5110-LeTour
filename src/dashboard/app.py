"""LeTour Analytics: entry point. Run from the repo root with: streamlit run src/dashboard/app.py"""
import streamlit as st

from lib import db, ui

st.set_page_config(page_title="LeTour Analytics", page_icon="🚴", layout="wide", initial_sidebar_state="expanded")

state = st.session_state

# Pulling new code updates the SQL files but not each member's database; this keeps them in step
db.ensure_current_views()

# Selections passed by ui.goto() from the previous page. Applied before any widget exists.
for key, value in state.pop("_pending", {}).items():
    state[key] = value

# Streamlit forgets a widget's value on pages that don't draw it; re-assigning keeps filters across pages.
for key in list(state.keys()):
    if key.startswith("w_"):
        state[key] = state[key]

ITEMS = [
    ("overview", "Overview", True),
    ("gc", "GC & Classifications", False),
    ("stages", "Stages", False),
    ("time_trials", "Time Trials", False),
    ("riders", "Riders", False),
    ("teams", "Teams", False),
    ("nations", "Nations", False),
    ("about", "About / Method", False),
]
pages = {slug: st.Page(ui.PAGES[slug], title=title, url_path=slug, default=default) for slug, title, default in ITEMS}
current = st.navigation(list(pages.values()), position="hidden")

ui.inject_css()

with st.sidebar:
    st.html(f'<div class="brand"><b>{ui.bike_logo()}LeTour Analytics</b><span>BT5110 · Group 16 · Tour 2025</span></div>')
    for slug, title, _ in ITEMS:
        with st.container(key=f"nav_{slug}"):
            st.page_link(pages[slug], label=title, width="stretch")
    st.html("""
    <div class="legend"><span class="eyebrow" style="color:#9AA0AC">Stage types</span>
    <span><i style="background:#8FB3D9"></i>Flat</span><span><i style="background:#E59A3C"></i>Hilly</span>
    <span><i style="background:#B5644A"></i>Mountain</span><span><i style="background:#8D7FE0"></i>Individual time-trial</span>
    <span class="src">Source: PostgreSQL · LeTour</span></div>
    """)

# Active nav item in leader yellow
active = next(slug for slug, page in pages.items() if page.url_path == current.url_path)
st.html(f"""<style>.st-key-nav_{active} a {{ background: #F5C400 !important; }}
.st-key-nav_{active} a p {{ color: #15171C !important; font-weight: 700 !important; }}</style>""")

current.run()
