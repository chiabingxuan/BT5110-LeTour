"""GC & Classifications: E1 leaderboard and stage-grain drill, E7 counterfactuals, E4 + req b parallel classifications."""
from html import escape

import pandas as pd
import streamlit as st

from lib import charts, filters, queries, ui
from lib import format as fmt

state = st.session_state

ui.header(["GC & Classifications"], "General classification &amp; jerseys")
f = filters.bar()
selected = queries.selected_stages(f)
stage_options = selected["stage_no"].tolist()

# GC-page options
if state.get("w_after") not in stage_options:
    state.w_after = stage_options[-1]
state.setdefault("w_cf", "Actual")
if not state.w_cf:
    state.w_cf = "Actual"
with st.container(key="card_gc_options"):
    c1, c2 = st.columns([1, 4], vertical_alignment="bottom")
    c1.selectbox("GC after stage", stage_options, key="w_after",
                 format_func=lambda n: f"Stage {n}" + (" (last selected)" if n == stage_options[-1] else ""))
    c2.segmented_control("Counterfactual GC · E7", ["Actual", "Without bonuses", "Without penalties"], key="w_cf")

after = int(state.w_after)
board = queries.gc_final(f, after)

COLUMNS = {
    "Actual": ("gc_rank", "cum_time", "gap"),
    "Without bonuses": ("no_bonus_rank", "no_bonus_time", "no_bonus_gap"),
    "Without penalties": ("no_penalty_rank", "no_penalty_time", "no_penalty_gap"),
}
rank_col, time_col, gap_col = COLUMNS[state.w_cf]

# ---------- E1 + E7: leaderboard ----------
top5 = board["rider_bib"].head(5).tolist()
valid = set(board["rider_bib"])
compare_set = [b for b in state.get("gc_compare", top5) if b in valid] or top5

replay = f" · <b>replayed {state.w_cf.lower()}</b>" if state.w_cf != "Actual" else ""
with ui.card("leaderboard", "GC leaderboard", tag="E1 · E7",
             sub=f"Cumulative adjusted time = Σ(finish − bonus + penalty){replay} · tick riders to compare them in the chart below (default: top 5)"):
    visible = f.narrow(board).sort_values([rank_col, "rider_bib"])
    show_all = st.toggle(f"Show all {len(visible)} riders", key="w_gc_all") if len(visible) > 20 else False
    shown = visible if show_all else visible.head(20)

    # The editor keeps its edits by row position, so each view of the table gets its own key and base selection
    signature = repr((f, after, state.w_cf, show_all))
    editor_key = f"gc_editor_{abs(hash(signature))}"
    base = state.setdefault(f"base_{editor_key}", list(compare_set))
    table = pd.DataFrame({
        "Compare": shown["rider_bib"].isin(base),
        "#": shown[rank_col],
        "Rider": shown["rider_name"],
        "Team": shown["team"],
        "Nat.": shown["rider_country"],
        "Time": shown[time_col].map(fmt.hms),
        "Gap": shown[gap_col].map(fmt.gap),
        "Bonus": shown["total_bonus"].map(fmt.bonus),
        "Penalty": shown["total_penalty"].map(fmt.penalty),
        "No-bonus rank": [fmt.rank_move(a, b) for a, b in zip(shown["gc_rank"], shown["no_bonus_rank"])],
        "No-penalty rank": [fmt.rank_move(a, b) for a, b in zip(shown["gc_rank"], shown["no_penalty_rank"])],
    }).reset_index(drop=True)
    edited = st.data_editor(
        table, key=editor_key, hide_index=True, width="stretch", disabled=[c for c in table.columns if c != "Compare"],
        column_config={
            "Compare": st.column_config.CheckboxColumn("Compare", width="small"),
            "#": st.column_config.NumberColumn("#", width="small"),
            "Team": st.column_config.TextColumn("Team", width="medium"),
            "Nat.": st.column_config.TextColumn("Nat.", width="small"),
        },
        height=min(38 + 35 * len(table), 740),
    )
    ticked = shown.reset_index(drop=True).loc[edited["Compare"].values, "rider_bib"].tolist()
    outside = [b for b in compare_set if b not in set(shown["rider_bib"])]
    new_compare = [b for b in compare_set if b in ticked] + [b for b in ticked if b not in compare_set] + outside
    state.gc_compare = new_compare or top5
    compare_set = state.gc_compare

    # E7 callout, computed
    def movement(label, column):
        actual = set(board.loc[board["gc_rank"] <= 10, "rider_bib"])
        replayed = set(board.loc[board[column] <= 10, "rider_bib"])
        names = board.set_index("rider_bib")["rider_name"]
        entered, left = replayed - actual, actual - replayed
        if not entered and not left:
            return f"{label}: top 10 unchanged, nobody enters or leaves."
        parts = []
        if entered:
            parts.append("enter the top 10: " + ", ".join(names[b] for b in entered))
        if left:
            parts.append("drop out: " + ", ".join(names[b] for b in left))
        return f"{label}: " + "; ".join(parts) + "."

    ui.html(f'<div class="callout">{movement("Without bonuses", "no_bonus_rank")} {movement("Without penalties", "no_penalty_rank")} '
            f'(Computed for GC after stage {after}.)</div>')
    exits = queries.exits()
    ui.note(f"{len(exits)} riders who left the race are not ranked; they show as DNF on the Riders page with their exit stage and reason.")

# ---------- E1: stage-grain drill ----------
names = board.set_index("rider_bib")["rider_name"]
if state.get("w_focus") not in compare_set:
    state.w_focus = compare_set[1] if len(compare_set) > 1 else compare_set[0]

in_range = selected[selected["stage_no"] <= after]
gc = queries.gc_by_stage(f, compare_set)
gc = gc[gc["stage_no"] <= after]
pivots = queries.pivotal(f, after)
pivots = pivots[pivots["rider_bib"].isin(compare_set)]

left, right = st.columns([5, 2])
with left:
    with ui.card("standing", "Overall GC standing after each stage", tag="E1", drill="Drill-down · stage grain",
                 sub="Ticked riders · GC position, 1 at the top · ◆ = each rider's pivotal stage · shaded = mountain stages"):
        st.pills("Rider in focus", compare_set, key="w_focus", format_func=lambda b: names[b], selection_mode="single")
        focus = state.w_focus if state.w_focus in compare_set else compare_set[0]
        st.plotly_chart(charts.gc_lines(gc, in_range, compare_set, "rank", pivots=pivots, focus=focus, height=340),
                        width="stretch", config={"displayModeBar": False}, key="standing_chart")
with right:
    with ui.card("pivotal", "Pivotal moment", drill="Rider in focus"):
        rider = board[board["rider_bib"] == focus].iloc[0]
        ui.html(f'<div class="big">{escape(rider.rider_name)}</div><div class="note">{escape(rider.team)} · {rider.rider_country} · GC {fmt.ordinal(rider.gc_rank)}</div>')
        row = pivots[pivots["rider_bib"] == focus]
        if row.empty:
            ui.note("Needs at least two stages in the selection.")
        else:
            p = row.iloc[0]
            s = in_range[in_range["stage_no"] == int(p.stage_no)].iloc[0]
            if p.delta_gap > 0:
                what = f"lost {fmt.gap(p.delta_gap).lstrip('+')} to the leader"
            elif p.delta_gap < 0:
                what = f"gained {fmt.gap(-p.delta_gap).lstrip('+')} on the leader"
            else:
                what = "no time change"
            ui.html(f'<div class="dark-box"><span class="eyebrow">Pivotal moment</span><b style="font-size:18px">Stage {s.stage_no} · {escape(s.route)}</b>'
                    f'<span>{s.type_label} · {fmt.long_date(s.date)} · GC {int(p.prev_rank)} → {int(p.gc_rank)} · {what}</span></div>')
        ui.note("Pivotal stage = the largest swing in the rider's gap to the GC leader; ties go to the bigger rank change, then the later stage.")
        if st.button("Open full rider profile →", key="open_profile"):
            ui.goto("riders", w_rider=int(focus))

# ---------- Req b + E4: parallel classifications ----------
with ui.card("parallel", "Parallel classifications", tag="Req. b · E4",
             sub="GC top 10 plus ticked riders, ranked side by side, with a mountain-only GC proxy"):
    state.setdefault("w_yrule", "Age at race start")
    if not state.w_yrule:
        state.w_yrule = "Age at race start"
    st.segmented_control("Young rider rule", ["Age at race start", "Official: born on or after 1 Jan 2000"], key="w_yrule")
    rule = "age" if state.w_yrule == "Age at race start" else "official"
    state.w_yrule_value = rule
    start = queries.stages()["date"].min()
    ui.note(f"Young = age at race start ({fmt.long_date(start)}) under {f.cutoff}; change the cutoff in the filter bar." if rule == "age"
            else "Official 2025 white-jersey rule: born on or after 1 Jan 2000.")

    compare = queries.compare(f, after, rule, f.cutoff)
    rows = f.narrow(compare[(compare["gc_rank"] <= 10) | compare["rider_bib"].isin(compare_set)])
    view = pd.DataFrame({
        "Rider": rows["rider_name"],
        f"Age at start ({fmt.medium_date(start)})": rows["age_at_start"],
        "GC": rows["gc_rank"],
        "Points*": rows["points_rank"].map(fmt.rank_or_dash),
        "KOM*": rows["kom_rank"].map(fmt.rank_or_dash),
        "Young": rows["young_rank"].map(fmt.rank_or_dash),
        "Mountain proxy": rows["mountain_rank"].map(fmt.rank_or_dash),
        "Proxy vs GC": rows["proxy_vs_gc"].map(fmt.difference),
    })
    ui.table(view, right=["Points*", "KOM*", "Young", "Mountain proxy", "Proxy vs GC"], moves=["Proxy vs GC"])
    ui.note("Age = age on the first stage date, never today's age. Mountain proxy = Σ adjusted time on the selected mountain stages, "
            "ranked among riders who finished all of them; ▼ = lower on mountains than overall. "
            "*Points and KOM are derived from finishing positions, not the official scoring (see About / Method).")
