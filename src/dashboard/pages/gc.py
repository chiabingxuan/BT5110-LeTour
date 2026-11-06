"""Chapter 2, Our leader vs the rivals: E1 GC descent of our leader against the rival leaders with the pivotal
stage, E7 slope chart of top-10 movement when bonuses and penalties are removed, E4 + req b classification dots."""
from html import escape

import pandas as pd
import streamlit as st

from lib import charts, filters, queries, team, ui
from lib import format as fmt

state = st.session_state
ctx = team.context()

ui.header(["2 · Our leader vs the rivals"], "Our leader vs the rivals")
f = filters.bar(rider_filters=True, young=True)
selected = queries.selected_stages(f)
stage_options = selected["stage_no"].tolist()

# GC-page options
if state.get("w_after") not in stage_options:
    state.w_after = stage_options[-1]
state.setdefault("w_cf_remove", [])
with st.container(key="card_gc_options"):
    c1, c2 = st.columns([1, 4], vertical_alignment="bottom")
    c1.selectbox("GC after stage", stage_options, key="w_after",
                 format_func=lambda n: f"Stage {n}" + (" (last selected)" if n == stage_options[-1] else ""))
    c2.pills("Replay the GC with these removed · E7 (choose one or both)", ["Bonuses", "Penalties"], selection_mode="multi", key="w_cf_remove")

after = int(state.w_after)
board = queries.gc_final(f, after)
all_riders = queries.riders().set_index("rider_bib")
names = all_riders["rider_name"]
team_of = all_riders["team"]
colours = {b: ctx.colour(t) for b, t in team_of.items()}
mine = set(all_riders.index[team_of == ctx.my])
in_range = selected[selected["stage_no"] <= after]

SCENARIOS = {
    (False, False): ("actual", "gc_rank", "cum_time", "gap", "Actual"),
    (True, False): ("no_bonus", "no_bonus_rank", "no_bonus_time", "no_bonus_gap", "without bonuses"),
    (False, True): ("no_penalty", "no_penalty_rank", "no_penalty_time", "no_penalty_gap", "without penalties"),
    (True, True): ("no_both", "no_both_rank", "no_both_time", "no_both_gap", "without bonuses and penalties"),
}
removed = state.w_cf_remove or []
scenario, rank_col, time_col, gap_col, scenario_label = SCENARIOS[("Bonuses" in removed, "Penalties" in removed)]


def team_leaders():
    """Our leader, each rival's leader and the GC leader at this point, in GC order."""
    ranked = board.sort_values("gc_rank")
    picks = []
    for t in (ctx.my, *ctx.rivals):
        picks += ranked.loc[ranked["team"] == t, "rider_bib"].head(1).tolist()
    picks += ranked["rider_bib"].head(1).tolist()
    order = list(ranked["rider_bib"])
    return sorted(set(picks), key=order.index) or order[:5]


# ---------- E1: our leader against the rival leaders, at stage grain ----------
valid = set(board["rider_bib"])
leaders = team_leaders()
everyone = queries.gc_by_stage(f)
left_race = sorted(set(everyone.loc[everyone["stage_no"] <= after, "rider_bib"]) - valid, key=lambda b: names[b])
state.w_gc_compare = [b for b in state.get("w_gc_compare", leaders) if b in valid] or leaders
state.w_gc_exited = [b for b in state.get("w_gc_exited", []) if b in left_race]
chart_set = state.w_gc_compare + state.w_gc_exited
our_leader = next((b for b in leaders if b in mine), None)
if state.get("w_focus") not in chart_set:
    state.w_focus = our_leader if our_leader in chart_set else chart_set[0]

gc = queries.gc_by_stage(f, chart_set)
gc = gc[gc["stage_no"] <= after]
pivots = queries.pivotal(f, after)
pivots = pivots[pivots["rider_bib"].isin(chart_set)]
ranked = board.set_index("rider_bib")

# Takeaway: our leader's place, and the closest rival leader
if our_leader is not None:
    me = ranked.loc[our_leader]
    where = "leads the race" if me.gc_rank == 1 else f"is {fmt.ordinal(me.gc_rank)}, {fmt.gap(me.gap)} behind the leader"
    rival_rows = board[board["team"].isin(ctx.rivals)].sort_values("gc_rank")
    rival = ""
    if not rival_rows.empty:
        r = rival_rows.iloc[0]
        diff = r.cum_time - me.cum_time
        rival = (f"; the best rival, {escape(r.rider_name)} ({escape(r.team)}), is {fmt.ordinal(r.gc_rank)}, "
                 f"{fmt.gap(abs(diff)).lstrip('+')} {'behind us' if diff > 0 else 'ahead of us'}")
    ui.takeaway(f"After stage {after}, our leader <b>{escape(me.rider_name)}</b> {where}{rival}.")
else:
    ui.takeaway(f"After stage {after}, none of our riders is still ranked in GC.")

left, right = st.columns([5, 2])
with left:
    with ui.card("standing", "Our leader against the rival leaders", tag="E1", drill="Drill-down · stage grain",
                 sub="Overall GC position after each stage, 1 at the top · line colour = team · ◆ = each rider's pivotal stage · shaded = mountain stages"):
        c1, c2 = st.columns([3, 2])
        c1.multiselect("Riders on the chart (default: each team's leader and the GC leader)", list(board["rider_bib"]), key="w_gc_compare",
                       format_func=lambda b: f"{ranked.loc[b, 'gc_rank']}. {names[b]} · {team_of[b]}", max_selections=10)
        c2.multiselect("Add riders who left the race", left_race, key="w_gc_exited",
                       format_func=lambda b: f"{names[b]} (left at stage {int(all_riders.loc[b, 'exit_stage'])})", placeholder="Search riders who left…")
        p1, p2 = st.columns([4, 1], vertical_alignment="bottom")
        p1.pills("Rider in focus", chart_set, key="w_focus", format_func=lambda b: names[b], selection_mode="single")
        focus = state.w_focus if state.w_focus in chart_set else chart_set[0]
        state.setdefault("w_rank_scale", "Log")
        if not state.w_rank_scale:
            state.w_rank_scale = "Log"
        p2.segmented_control("Rank axis", ["Log", "Linear"], key="w_rank_scale")
        exit_stages = {b: int(all_riders.loc[b, "exit_stage"]) for b in chart_set if b in left_race}
        labels = {b: names[b].split()[-1] for b in chart_set}
        st.plotly_chart(charts.gc_lines(gc, in_range, chart_set, "rank", pivots=pivots, focus=focus, exits=exit_stages, height=360,
                                        rank_scale=state.w_rank_scale.lower(), colours=colours, bold=mine, end_labels=labels),
                        width="stretch", config={"displayModeBar": False}, key="standing_chart")
        ui.html(f"<div>{team.swatches(ctx)}</div>")
with right:
    with ui.card("pivotal", "Pivotal moment", drill="Rider in focus"):
        rider = all_riders.loc[focus]
        standing = f"GC {fmt.ordinal(ranked.loc[focus, 'gc_rank'])}" if focus in valid else f"DNF – stage {int(rider.exit_stage)} ({rider.exit_reason})"
        ui.html(f'<div class="big">{escape(rider.rider_name)}</div><div class="note">{ctx.label(rider.team)} · {rider.rider_country} · {standing}</div>')
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

with st.expander("Show data: full GC leaderboard"):
    visible = f.narrow(board).sort_values([rank_col, "rider_bib"])
    show_all = st.toggle(f"Show all {len(visible)} riders", key="w_gc_all") if len(visible) > 20 else False
    shown = visible if show_all else visible.head(20)
    if scenario != "actual":
        ui.note(f"Ranks and times replayed {scenario_label}.")
    table = pd.DataFrame({
        "#": shown[rank_col], "Rider": shown["rider_name"], "Team": shown["team"], "Nat.": shown["rider_country"],
        "Time": shown[time_col].map(fmt.hms), "Gap": shown[gap_col].map(fmt.gap),
        "Bonus": shown["total_bonus"].map(fmt.bonus), "Penalty": shown["total_penalty"].map(fmt.penalty),
        "No bonus": [fmt.rank_move(a, b) for a, b in zip(shown["gc_rank"], shown["no_bonus_rank"])],
        "No penalty": [fmt.rank_move(a, b) for a, b in zip(shown["gc_rank"], shown["no_penalty_rank"])],
        "Neither": [fmt.rank_move(a, b) for a, b in zip(shown["gc_rank"], shown["no_both_rank"])],
    }).reset_index(drop=True)
    ours = table.style.apply(lambda c: [f"color:{team.MY};font-weight:700" if t == ctx.my else "" for t in table["Team"]], subset=["Rider", "Team"])
    ui.table(table, right=["Time", "Gap", "Bonus", "Penalty"], moves=["No bonus", "No penalty", "Neither"], styler=ours,
             height=min(40 + 35 * len(table), 740))
    ui.note(f"{len(queries.exits())} riders who left the race have no final rank; they show as DNF on the Rider profile page.")

# ---------- E7: slope chart of the top 10, actual against the replay ----------
replay_cf = scenario if scenario != "actual" else "no_both"
replay_rank = rank_col if scenario != "actual" else "no_both_rank"
replay_name = scenario_label if scenario != "actual" else "without bonuses and penalties"
with ui.card("movement", "Who moves in and out of the top 10", tag="E7",
             sub=f"GC after stage {after}: actual places (left) against the replay {replay_name} (right) · choose what to remove at the top of the page"):
    near = board[(board["gc_rank"] <= 13) | (board[replay_rank] <= 13)].sort_values("gc_rank")
    rows = pd.DataFrame({
        "name": near["rider_name"], "colour": [ctx.colour(t) for t in near["team"]],
        "left": near["gc_rank"].astype(int), "right": near[replay_rank].astype(int), "bold": near["team"] == ctx.my,
    })
    entered = near[(near["gc_rank"] > 10) & (near[replay_rank] <= 10)]
    left_top = near[(near["gc_rank"] <= 10) & (near[replay_rank] > 10)]
    if entered.empty and left_top.empty:
        biggest = near.assign(move=(near["gc_rank"] - near[replay_rank]).abs()).sort_values("move", ascending=False).iloc[0]
        moved = (f"; the biggest move is {escape(biggest.rider_name)}, {int(biggest.gc_rank)} → {int(biggest[replay_rank])}"
                 if biggest.move else "; no rider near the cut changes place")
        ui.takeaway(f"Removing {replay_name.removeprefix('without ')} changes nobody in the top 10 after stage {after}{moved}.")
    else:
        parts = []
        if not entered.empty:
            parts.append(", ".join(escape(n) for n in entered["rider_name"]) + " would enter")
        if not left_top.empty:
            parts.append(", ".join(escape(n) for n in left_top["rider_name"]) + " would drop out")
        ui.takeaway(f"Without {replay_name.removeprefix('without ')}, " + " and ".join(parts) + f" of the top 10 after stage {after}.")
    st.plotly_chart(charts.slope(rows, "Actual", "Replay"), width="stretch", config={"displayModeBar": False}, key="slope_chart")
    ui.note("Shaded = top 10 · thick lines = our riders and anyone crossing the dashed cut · ▲▼ = places gained or lost in the replay.")

    with st.expander("Show data: around the cut, and stage by stage"):
        around = board[board["gc_rank"].between(8, 13)]
        ui.table(pd.DataFrame({
            "Rider": around["rider_name"], "Actual": around["gc_rank"], "Bonus": around["total_bonus"].map(fmt.bonus),
            "Penalty": around["total_penalty"].map(fmt.penalty),
            "No bonus": [fmt.rank_move(a, b) for a, b in zip(around["gc_rank"], around["no_bonus_rank"])],
            "No penalty": [fmt.rank_move(a, b) for a, b in zip(around["gc_rank"], around["no_penalty_rank"])],
            "Neither": [fmt.rank_move(a, b) for a, b in zip(around["gc_rank"], around["no_both_rank"])],
        }), moves=["No bonus", "No penalty", "Neither"])
        moves = queries.top10_movement(f, replay_cf)
        moves = moves[moves["stage_no"] <= after]
        if moves.empty:
            ui.note(f"At no stage up to stage {after} does this replay change who is in the top 10.")
        else:
            grouped = moves.groupby("stage_no").apply(lambda g: pd.Series({
                "Enters": ", ".join(g.loc[g["movement"] == "enters", "rider_name"]) or "—",
                "Leaves": ", ".join(g.loc[g["movement"] == "leaves", "rider_name"]) or "—",
            }), include_groups=False).reset_index().rename(columns={"stage_no": "Stage"})
            ui.html(f'<div class="eyebrow">Stage by stage, {replay_name}</div>')
            ui.table(grouped)

# ---------- Req b + E4: parallel classifications as dots ----------
with ui.card("parallel", "Parallel classifications", tag="Req. b · E4",
             sub="Each rider's rank in overall GC, the young rider GC and a mountain-only GC proxy · GC top 10, our riders and the riders on the chart above"):
    state.setdefault("w_yrule", "Age at race start")
    if not state.w_yrule:
        state.w_yrule = "Age at race start"
    st.segmented_control("Young rider rule", ["Age at race start", "Official: born on or after 1 Jan 2000"], key="w_yrule")
    rule = "age" if state.w_yrule == "Age at race start" else "official"
    state.w_yrule_value = rule
    start = queries.stages()["date"].min()

    compare = queries.compare(f, after, rule, f.cutoff)
    picked = compare[(compare["gc_rank"] <= 10) | compare["rider_bib"].isin(mine) | compare["rider_bib"].isin(chart_set)]
    picked = f.narrow(picked).head(18)
    if picked.empty:
        ui.note("No ranked rider matches the current filter.")
    else:
        # Rider names take their team's colour when they ride for us or a rival
        dots = pd.DataFrame({
            "label": [f'<span style="color:{ctx.colour(t) if ctx.is_focus(t) else "#15171C"}">{g}. {escape(n)}</span>'
                      for g, n, t in zip(picked["gc_rank"], picked["rider_name"], picked["team"])],
            "gc": picked["gc_rank"], "young": picked["young_rank"], "mountain": picked["mountain_rank"],
        })
        diverge = picked.dropna(subset=["proxy_vs_gc"])
        if not diverge.empty:
            d = diverge.loc[diverge["proxy_vs_gc"].abs().idxmax()]
            direction = "higher" if d.proxy_vs_gc > 0 else "lower"
            ui.takeaway(f"Biggest gap between terrain and overall: <b>{escape(d.rider_name)}</b> ranks {abs(int(d.proxy_vs_gc))} places "
                        f"{direction} on the mountain proxy ({fmt.ordinal(d.mountain_rank)}) than in overall GC ({fmt.ordinal(d.gc_rank)}).")
        st.plotly_chart(charts.rank_dots(dots), width="stretch", config={"displayModeBar": False}, key="dots_chart")
        ui.note((f"Young = age at race start ({fmt.long_date(start)}) under {f.cutoff}; change the cutoff in the filter bar. " if rule == "age"
                 else "Official 2025 white-jersey rule: born on or after 1 Jan 2000. ")
                + "Mountain GC proxy = Σ adjusted time on the selected mountain stages, ranked among riders who finished all of them. "
                  "Names in our colour or a rival's colour belong to those teams.")

    with st.expander("Show data: classification table, with Points and KOM"):
        c1, c2 = st.columns(2)
        show_all_par = c1.toggle(f"Show all {len(f.narrow(compare))} riders", key="w_par_all")
        show_derived = c2.toggle("Add Points and KOM (req. b)", key="w_par_derived")
        rows = f.narrow(compare if show_all_par else compare[(compare["gc_rank"] <= 10) | compare["rider_bib"].isin(chart_set)])
        columns = {"Rider": rows["rider_name"], "Team": rows["team"], "Age": rows["age_at_start"], "Overall GC": rows["gc_rank"]}
        if show_derived:
            columns["Points*"] = rows["points_rank"].map(fmt.rank_or_dash)
            columns["KOM*"] = rows["kom_rank"].map(fmt.rank_or_dash)
        columns["Young GC"] = rows["young_rank"].map(fmt.rank_or_dash)
        columns["Mountain GC Proxy"] = rows["mountain_rank"].map(fmt.rank_or_dash)
        columns["Proxy vs GC"] = rows["proxy_vs_gc"].map(fmt.signed_places)
        view = pd.DataFrame(columns)
        text_columns = [c for c in view.columns if c not in ("Rider", "Team", "Age", "Overall GC")]
        ui.table(view, moves=["Proxy vs GC"], column_config={c: st.column_config.TextColumn(c, alignment="right") for c in text_columns})
        derived_note = " *Points and KOM are derived from finishing positions, not the official scoring (see About / Method)." if show_derived else ""
        ui.note(f"Age = age at race start ({fmt.medium_date(start)}), never today's age. "
                "Proxy vs GC = Overall GC − proxy rank: + means higher on the mountains than overall, − means lower." + derived_note)
