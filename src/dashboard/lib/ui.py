"""Shared page furniture: theme CSS, cards with E-number tags, breadcrumbs, tiles and tables."""
from base64 import b64encode
from html import escape

import streamlit as st

TYPE_COLOURS = {"flat": "#8FB3D9", "hilly": "#E59A3C", "mountain": "#B5644A", "individual time-trial": "#8D7FE0"}
TYPE_FG = {"flat": "#15171C", "hilly": "#15171C", "mountain": "#FFFFFF", "individual time-trial": "#15171C"}
TYPE_LABELS = {"flat": "Flat", "hilly": "Hilly", "mountain": "Mountain", "individual time-trial": "ITT"}

PAGES = {
    "overview": "pages/overview.py",
    "gc": "pages/gc.py",
    "stages": "pages/stages.py",
    "time_trials": "pages/time_trials.py",
    "riders": "pages/riders.py",
    "teams": "pages/teams.py",
    "nations": "pages/nations.py",
    "about": "pages/about.py",
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow:wght@400;500;600;700&family=Barlow+Condensed:wght@600;700&display=swap');
html, body, [class*="stApp"], button, input, select, textarea { font-family: 'Barlow', system-ui, sans-serif; }
[data-testid="stMainBlockContainer"] { padding: 1.6rem 2rem 3rem; max-width: 1320px; }
[data-testid="stHeader"] { background: transparent; }
h1.page-title { font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 40px; line-height: 1.05; margin: 2px 0 0; padding: 0; color: #15171C; }
.eyebrow { font-size: 12px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #5B6170; }
.note { font-size: 12.5px; color: #5B6170; line-height: 1.45; }
.num { font-variant-numeric: tabular-nums; }

/* Cards: st.container(key="card_*" or "drill_*") */
[class*="st-key-card_"], [class*="st-key-drill_"] { background: #FFFFFF; border: 1px solid #E3E5EA; border-radius: 12px; padding: 18px 20px; }
[class*="st-key-drill_"] { border: 2px solid #2E5FA8; }
.card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
.card-head h3 { margin: 0; padding: 0; font-family: 'Barlow', sans-serif; font-size: 18px; font-weight: 700; color: #15171C; }
.card-head .sub { font-size: 13px; color: #5B6170; line-height: 1.4; margin-top: 2px; }
.card-head .drill-label { font-size: 12px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: #2E5FA8; }
.tag { font-size: 12px; font-weight: 600; color: #5B6170; background: #F3F4F6; border-radius: 999px; padding: 3px 9px; white-space: nowrap; }

/* KPI tiles */
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.kpi { background: #FFFFFF; border: 1px solid #E3E5EA; border-radius: 12px; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.kpi b { font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 36px; line-height: 1; font-variant-numeric: tabular-nums; color: #15171C; }

/* Sidebar */
[data-testid="stSidebar"] { min-width: 240px !important; max-width: 260px !important; }
.brand b { font-family: 'Barlow Condensed', sans-serif; font-size: 24px; color: #FFFFFF; letter-spacing: .02em; display: flex; align-items: center; gap: 8px; }
.brand span { font-size: 13px; color: #9AA0AC; }
.legend { display: flex; flex-direction: column; gap: 8px; font-size: 13px; color: #9AA0AC; margin-top: 24px; }
.legend i { width: 10px; height: 10px; border-radius: 3px; display: inline-block; margin-right: 8px; }
.legend .src { border-top: 1px solid #2C3039; padding-top: 10px; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a { border-radius: 8px; min-height: 44px; padding: 0 12px; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover { background: #262A33; }
[data-testid="stSidebar"] [data-testid="stPageLink"] p { font-size: 15px; font-weight: 500; color: #C9CCD3; }

/* Rider picker wraps instead of hiding chips; daily-trace tiles stack stage over rank */
[data-testid="stMultiSelect"] .react-aria-ComboBox, [data-testid="stMultiSelect"] [role="group"], [data-testid="stMultiSelectTagsContainer"] { height: auto !important; max-height: none !important; }
[data-testid="stMultiSelectTagsContainer"] { flex-wrap: wrap !important; overflow: visible !important; }
[class*="st-key-trace_"] button p { word-spacing: 100vw; line-height: 1.25; white-space: normal; text-align: center; font-size: 13px; }

/* The filter card already draws the frame around its collapsible section */
.st-key-card_filters [data-testid="stExpander"] details { border: 0; }
.st-key-card_filters { padding: 4px 8px 10px 8px; gap: 2px; }
.st-key-card_filters .note { padding: 0 16px; }

/* Small helpers */
.bar-track { height: 10px; background: #F0F1F4; border-radius: 4px; overflow: hidden; }
.bar-track i { display: block; height: 100%; border-radius: 4px; }
.hrow { display: grid; align-items: center; gap: 10px; font-size: 14px; padding: 4px 0; }
.strip { display: grid; gap: 3px; }
.sq { height: 22px; border-radius: 4px; font-size: 10px; font-weight: 700; display: flex; align-items: center; justify-content: center; border: 1px solid #E3E5EA; font-variant-numeric: tabular-nums; }
.inf-list { max-height: 330px; overflow-y: auto; border: 1px solid #E3E5EA; border-radius: 8px; }
.inf { display: grid; grid-template-columns: minmax(130px, 190px) 1fr; gap: 10px; padding: 8px 12px; border-bottom: 1px solid #F0F1F4; font-size: 13px; line-height: 1.5; }
.dot { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.badge { width: 22px; height: 22px; flex: none; border-radius: 999px; background: #F5C400; color: #15171C; font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }
.up { color: #1E6B3E; font-weight: 700; } .down { color: #A1262C; font-weight: 700; }
.dark-box { background: #15171C; color: #FFFFFF; border-radius: 10px; padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; font-size: 14px; line-height: 1.45; }
.dark-box .eyebrow { color: #F5C400; }
.callout { padding: 10px 12px; border-radius: 8px; background: #EEF3FA; color: #1F4E8C; font-size: 13px; line-height: 1.5; }
.banner { background: #15171C; color: #FFFFFF; border-radius: 12px; display: flex; flex-wrap: wrap; overflow: hidden; }
.banner .l { flex: 999 1 380px; padding: 22px 26px; display: flex; flex-direction: column; gap: 6px; }
.banner .t { font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 40px; line-height: 1.05; }
.banner .stats { flex: 1 1 420px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.banner .stats div { padding: 20px; border-left: 1px solid #2C3039; display: flex; flex-direction: column; gap: 4px; }
.banner .eyebrow { color: #9AA0AC; }
.big { font-family: 'Barlow Condensed', sans-serif; font-weight: 700; font-size: 28px; font-variant-numeric: tabular-nums; }
.leader { display: flex; align-items: center; gap: 12px; padding: 9px 12px; border: 1px solid #E3E5EA; border-radius: 10px; margin-bottom: 8px; }
.leader .who { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.leader .stat { font-size: 13px; color: #5B6170; text-align: right; font-variant-numeric: tabular-nums; }
</style>
"""


def inject_css():
    st.html(CSS)


def svg_img(svg, size):
    """st.html removes inline <svg>, so icons are drawn as <img> tags with a data URI."""
    data = b64encode(svg.encode("utf-8")).decode("ascii")
    return f'<img alt="" width="{size}" height="{size}" style="flex:none" src="data:image/svg+xml;base64,{data}">'


def jersey(fill, stroke, size=32):
    return svg_img(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M8 3l-5 3 2 4 2-1v12h10V9l2 1 2-4-5-3c-.5 1.5-2 2.5-4 2.5S8.5 4.5 8 3z" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.2"/></svg>', size)


def bike_logo(size=26):
    return svg_img(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#F5C400" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
        '<circle cx="5.5" cy="16" r="3.5"/><circle cx="18.5" cy="16" r="3.5"/><path d="M5.5 16l4-7h6l3 7M9.5 9l3 7 3-7M8 6.5h3"/></svg>', size)


def html(content):
    st.html(content)


def note(text):
    st.html(f'<div class="note">{text}</div>')


def goto(page, **state):
    """Opens another page, passing selections through session state (applied at the top of app.py)."""
    st.session_state["_pending"] = state
    st.switch_page(PAGES[page])


def header(crumbs, title, schema_toggle=True):
    """Breadcrumb + page title. crumbs is a list of labels after Overview."""
    path = " › ".join(escape(str(c)) for c in ["Overview", *crumbs])
    left, right = st.columns([5, 2], vertical_alignment="bottom")
    left.html(f'<div class="eyebrow">{path}</div><h1 class="page-title">{title}</h1>')
    if schema_toggle:
        right.segmented_control(
            "Query schema", ["Normalized", "Star schema"], default="Normalized", disabled=True,
            label_visibility="collapsed", key="schema_toggle",
            help="The star schema toggle is enabled once the Task 4 star schema is built.",
        )


def card(key, title, sub=None, tag=None, drill=None):
    """Opens a card container with a title, caption and E-number tag. drill=label makes it a blue drill panel."""
    prefix = "drill_" if drill else "card_"
    container = st.container(key=f"{prefix}{key}")
    label = f'<div class="drill-label">{drill}</div>' if drill else ""
    subtitle = f'<div class="sub">{sub}</div>' if sub else ""
    pill = f'<span class="tag">{tag}</span>' if tag else ""
    container.html(f'<div class="card-head"><div>{label}<h3>{title}</h3>{subtitle}</div>{pill}</div>')
    return container


def kpi_tiles(tiles):
    """tiles: (label, value, caption) tuples."""
    cells = "".join(
        f'<div class="kpi"><span class="eyebrow">{label}</span><b>{value}</b><span class="note">{caption}</span></div>'
        for label, value, caption in tiles
    )
    st.html(f'<div class="kpis">{cells}</div>')


def bar_html(pct, colour="#7C8291"):
    pct = max(0, min(100, pct))
    return f'<div class="bar-track"><i style="width:{pct:.1f}%;background:{colour}"></i></div>'


def _move_colour(value):
    if isinstance(value, str):
        if value.startswith(("▲", "+")):
            return "color:#1E6B3E;font-weight:700"
        if value.startswith(("▼", "−")):
            return "color:#A1262C;font-weight:700"
    return ""


def table(df, *, key=None, right=(), moves=(), select=None, height=None, column_config=None, styler=None):
    """Draws a DataFrame. right: right-aligned columns; moves: columns coloured by their ▲▼ prefix;
    select: None, 'row' or 'cell'. Returns the Streamlit selection event when selectable."""
    style = df.style if styler is None else styler
    if right:
        style = style.set_properties(subset=list(right), **{"text-align": "right"})
    if moves:
        style = style.map(_move_colour, subset=list(moves))
    kwargs = {}
    if select:
        # Row tables also listen for cell clicks, so a click anywhere on a row selects it
        kwargs = {"on_select": "rerun", "selection_mode": ["single-row", "single-cell"] if select == "row" else "single-cell"}
    if key:
        kwargs["key"] = key
    return st.dataframe(
        style, hide_index=True, width="stretch", column_config=column_config,
        height=height if height is not None else min(40 + 35 * len(df), 420), **kwargs,
    )


def new_row(event, key):
    """Returns the selected row number only when the selection changed since the last run."""
    rows = tuple(event.selection.rows) or tuple(int(cell[0]) for cell in event.selection.cells)
    previous = st.session_state.get(f"_prev_{key}")
    st.session_state[f"_prev_{key}"] = rows
    return rows[0] if rows and rows != previous else None


def new_cell(event, key):
    """Returns (row, column) only when the selected cell changed since the last run."""
    cells = tuple(tuple(c) for c in event.selection.cells)
    previous = st.session_state.get(f"_prev_{key}")
    st.session_state[f"_prev_{key}"] = cells
    return cells[0] if cells and cells != previous else None


def stage_button_css(stage_rows, prefix, selected=None, selected_only_in=None, heights=None):
    """Colours keyed stage buttons by stage type. stage_rows needs stage_no and type."""
    rules = []
    for row in stage_rows.itertuples():
        selector = f".st-key-{prefix}{row.stage_no} button"
        faded = selected_only_in is not None and row.stage_no not in selected_only_in
        border = "3px solid #15171C" if row.stage_no == selected else "1px solid transparent"
        rule = (f"background:{TYPE_COLOURS[row.type]};border:{border};opacity:{0.35 if faded else 1};"
                f"padding:0;min-height:40px;")
        if heights:
            rule += f"height:{heights[row.stage_no]}px;align-items:flex-end;padding-bottom:6px;"
        rules.append(f"{selector}{{{rule}}}")
        rules.append(f"{selector} p{{color:{TYPE_FG[row.type]};font-weight:700;font-size:14px;}}")
    st.html("<style>" + "".join(rules) + "</style>")
