"""Chapter 1, Where do we stand: my team's position (KPI tiles with the change since the previous stage),
the E10 GC storyline with my riders highlighted, the route, leaders, distance mix and exits."""
from html import escape

import streamlit as st

from lib import charts, filters, queries, team, ui
from lib import format as fmt

state = st.session_state

ctx = team.context()
ui.header(["1 · Where do we stand"], "Where do we stand?")
f = filters.bar(young=True)
selected = queries.selected_stages(f)
final = queries.gc_final(f)
all_riders = queries.riders().set_index("rider_bib")
team_of = all_riders["team"]
colours = {b: ctx.colour(t) for b, t in team_of.items()}
mine = set(all_riders.index[all_riders["team"] == ctx.my])

# ---------- My team: KPI tiles, each with its change since the previous selected stage ----------
gc_all = queries.gc_by_stage(f)
best_by_stage = queries.best_team_by_stage(f)
last_seq = int(selected["seq"].max())
last_no = int(selected.loc[selected["seq"] == last_seq, "stage_no"].iloc[0])
prev_no = int(selected.loc[selected["seq"] == last_seq - 1, "stage_no"].iloc[0]) if last_seq > 1 else None


def move(before, after, lower_is_better=True, unit=""):
    """▲/▼ change since the previous stage as HTML; empty without a previous stage."""
    if prev_no is None or before is None or after is None:
        return ""
    change = (before - after) if lower_is_better else (after - before)
    if change == 0:
        return f'<span class="note">= since stage {prev_no}</span>'
    css, arrow = ("up", "▲") if change > 0 else ("down", "▼")
    return f'<span class="{css}">{arrow} {abs(change)}{unit}</span> <span class="note">since stage {prev_no}</span>'


def best_of_mine(seq):
    rows = gc_all[(gc_all["seq"] == seq) & gc_all["rider_bib"].isin(mine)]
    return rows.sort_values("gc_rank").iloc[0] if not rows.empty else None


now, before = best_of_mine(last_seq), best_of_mine(last_seq - 1)
bt_now = best_by_stage[(best_by_stage["seq"] == last_seq) & (best_by_stage["team"] == ctx.my)]
bt_before = best_by_stage[(best_by_stage["seq"] == last_seq - 1) & (best_by_stage["team"] == ctx.my)]
bt_leader = best_by_stage[(best_by_stage["seq"] == last_seq) & (best_by_stage["team_rank"] == 1)]
results = queries.top10_rows(f, team=ctx.my)
wins = results[results["rank"] == 1]
in_race = lambda seq: int(gc_all[(gc_all["seq"] == seq) & gc_all["rider_bib"].isin(mine)]["rider_bib"].nunique())
riders_now, riders_before = in_race(last_seq), (in_race(last_seq - 1) if last_seq > 1 else None)

tiles = []
if now is not None:
    lead = "in yellow" if now.gc_rank == 1 else f"{fmt.gap(now.gap)} to yellow"
    tiles.append(("Best GC rider", fmt.ordinal(now.gc_rank),
                  f"{escape(now.rider_name)} · {lead}<br>{move(None if before is None else int(before.gc_rank), int(now.gc_rank), unit=' place(s)')}"))
else:
    tiles.append(("Best GC rider", "—", "no rider of ours is still in the race"))
if not bt_now.empty:
    b = bt_now.iloc[0]
    if b.team_rank == 1:
        second = best_by_stage[(best_by_stage["seq"] == last_seq) & (best_by_stage["team_rank"] == 2)]
        detail = f"leads by {fmt.gap(second.iloc[0].gap).lstrip('+')}" if not second.empty else "leads"
    else:
        detail = f"{fmt.gap(b.gap)} behind {escape(bt_leader.iloc[0].team)}"
    tiles.append(("Best Team", fmt.ordinal(b.team_rank),
                  f"{detail}<br>{move(None if bt_before.empty else int(bt_before.iloc[0].team_rank), int(b.team_rank), unit=' place(s)')}"))
else:
    tiles.append(("Best Team", "—", "not ranked: fewer than 3 finishers on a stage"))
won_last = (wins["stage_no"] == last_no).any()
tiles.append(("Stage wins", len(wins),
              (", ".join(f"S{n}" for n in wins["stage_no"]) or "none yet") + ("<br><span class='up'>▲ won the last stage</span>" if won_last else "")))
tiles.append(("Top-10 finishes", len(results), f"{results['rider_bib'].nunique()} of our riders"))
tiles.append(("Riders still in", riders_now, f"of {len(mine)} starters<br>{move(riders_before, riders_now, lower_is_better=False)}"))
ui.kpi_tiles(tiles)

if now is not None:
    sentence = f"After stage {last_no}, <b>{escape(now.rider_name)}</b> is {'in yellow' if now.gc_rank == 1 else fmt.ordinal(now.gc_rank) + ' in GC, ' + fmt.gap(now.gap) + ' behind'}"
else:
    sentence = f"After stage {last_no}, none of our riders is left in GC"
if not bt_now.empty:
    b = bt_now.iloc[0]
    sentence += f"; {escape(ctx.my)} {'lead' if b.team_rank == 1 else 'are ' + fmt.ordinal(b.team_rank) + ' in'} the Best Team classification"
ui.takeaway(sentence + f", with {len(wins)} stage win{'' if len(wins) == 1 else 's'}.")

# ---------- Route strip ----------
all_stages = queries.stages()
with ui.card("route", "The route, stage by stage", "Bar height = distance · colour = stage type · faded = outside the filter · click a stage to open it"):
    longest = all_stages["dist_km"].max()
    heights = {row.stage_no: int(44 + row.dist_km / longest * 90) for row in all_stages.itertuples()}
    ui.stage_button_css(all_stages, "route_", selected_only_in=set(selected["stage_no"]), heights=heights)
    columns = st.columns(21, gap=None, vertical_alignment="bottom")
    for column, row in zip(columns, all_stages.itertuples()):
        if column.button(str(row.stage_no), key=f"route_{row.stage_no}", help=f"{row.stage_label} · {row.type_label} · {row.dist_km} km", width="stretch"):
            ui.goto("stages", w_stage=row.stage_no)


# ---------- E10 GC storyline ----------
def add_team_riders(pickable):
    team = state.add_team
    if team:
        add = pickable.loc[pickable["team"] == team, "rider_bib"].tolist()
        state.w_story = (state.w_story + [b for b in add if b not in state.w_story])[:10]
    state.add_team = None


def reset_story(default):
    state.w_story = default


def story_default():
    """My two best riders, each rival's best rider and the GC leader, in GC order."""
    ranked = final.assign(team=final["rider_bib"].map(team_of))
    picks = ranked[ranked["team"] == ctx.my]["rider_bib"].head(2).tolist()
    for rival in ctx.rivals:
        picks += ranked[ranked["team"] == rival]["rider_bib"].head(1).tolist()
    picks += ranked["rider_bib"].head(1).tolist()
    order = list(ranked["rider_bib"])
    return sorted(set(picks), key=order.index)[:10] or ranked["rider_bib"].head(5).tolist()


with ui.card("story", "GC storyline: our riders against the rivals", tag="E10",
             sub="Line colour = team (ours bold) · shaded = mountain stages · numbered flags = yellow jersey changes"):
    # Finishers in GC order, then riders who left the race and so have no final rank
    top5 = story_default()
    in_gc = set(gc_all["rider_bib"])
    left = sorted((b for b in in_gc if b not in set(final["rider_bib"])), key=lambda b: all_riders.loc[b, "rider_name"])
    names = dict(zip(final["rider_bib"], final["gc_rank"].astype(str) + ". " + final["rider_name"]))
    names.update({b: f"{all_riders.loc[b, 'rider_name']} (left at stage {int(all_riders.loc[b, 'exit_stage'])})" for b in left})
    pickable = all_riders.loc[list(names)].reset_index()
    valid = set(names)
    state.w_story = [b for b in state.get("w_story", top5) if b in valid] or top5

    c1, c2, c3 = st.columns([5, 2, 1.1], vertical_alignment="bottom")
    c1.multiselect("Riders on the chart (default: our two best, each rival's best and the leader; search any rider)", list(names), key="w_story", format_func=names.get, max_selections=10)
    c2.selectbox("Add a team's riders", queries.team_names()["name"].tolist(), key="add_team", index=None,
                 placeholder="Choose team…", on_change=add_team_riders, args=(pickable,))
    c3.button("Reset", on_click=reset_story, args=(top5,), width="stretch", help="Our two best riders, each rival's best rider and the GC leader")

    state.setdefault("w_story_view", "GC rank")
    if not state.w_story_view:
        state.w_story_view = "GC rank"
    state.setdefault("w_rank_scale", "Log")
    if not state.w_rank_scale:
        state.w_rank_scale = "Log"
    m1, m2 = st.columns([1, 3], vertical_alignment="bottom")
    m1.segmented_control("Measure", ["GC rank", "Cumulative time"], key="w_story_view", label_visibility="collapsed")
    measure = "rank" if state.w_story_view == "GC rank" else "time"
    if measure == "rank":
        m2.segmented_control("Rank axis", ["Log", "Linear"], key="w_rank_scale", label_visibility="collapsed",
                             help="Log gives the top places the most room; Linear spaces every rank evenly.")

    bibs = state.w_story
    gc = queries.gc_by_stage(f, bibs) if bibs else None
    inflections = queries.inflections(f, bibs) if bibs else None
    yellow = queries.yellow(f)
    if bibs:
        exits = {b: int(all_riders.loc[b, "exit_stage"]) for b in bibs if b in left}
        labels = {b: all_riders.loc[b, "rider_name"].split()[-1] for b in bibs}
        st.plotly_chart(charts.gc_lines(gc, selected, bibs, measure, inflections, yellow, exits=exits, rank_scale=state.w_rank_scale.lower(),
                                        colours=colours, bold=mine, end_labels=labels),
                        width="stretch", config={"displayModeBar": False}, key="story_chart")
        ui.html(f'<div>{team.swatches(ctx)}</div>')
    ui.note(("Overall GC position after each stage, 1 at the top; crossings are reshuffles; " + ("the log rank axis gives the top places the most room." if state.w_rank_scale == "Log" else "the linear rank axis spaces every place evenly.")
             if measure == "rank" else
             "Cumulative adjusted time shown as gap to the leader (rider's total − leader's); hover for the full total.")
            + " ○ = GC rank changed vs the previous stage · large yellow dot = takes the yellow jersey · × = left the race.")

    left, right = st.columns([1, 2])
    with left:
        rows = yellow[yellow["is_change"]]
        lines = "".join(
            f'<div style="display:flex;gap:10px;align-items:center;font-size:14px;padding:3px 0"><span class="badge">{r.change_no}</span>'
            f'<span>Stage {r.stage_no}: <b>{escape(r.holder_name)}</b> {"first yellow" if r.change_no == 1 else "takes yellow"}</span></div>'
            for r in rows.itertuples()
        )
        ties = yellow[yellow["is_tie"]]
        tie_note = "".join(
            f'<div class="note" style="margin-top:6px">Stage {r.stage_no}: level on time ({escape(r.tied_with)}); the lower sum of stage placings puts {escape(r.holder_name)} first.</div>'
            for r in ties.itertuples()
        )
        biggest = ""
        if bibs and not inflections.empty:
            swings = inflections.assign(swing=inflections["delta_gap"].abs()).groupby("stage_no").agg(n=("rider_bib", "count"), swing=("swing", "sum"))
            top = swings.sort_values(["n", "swing"], ascending=False).iloc[0]
            stage = selected[selected["stage_no"] == swings.sort_values(["n", "swing"], ascending=False).index[0]].iloc[0]
            biggest = (f'<div class="dark-box" style="margin-top:10px"><span class="eyebrow">Biggest reshuffle</span>'
                       f'<span>Stage {stage.stage_no} ({stage.type_label}, {escape(stage.route)}): {int(top.n)} of {len(bibs)} plotted riders change GC position; '
                       f'{top.swing / 60:.0f} min of gap moves.</span></div>')
        ui.html(f'<div class="eyebrow" style="margin-bottom:6px">Yellow jersey changes</div>{lines}{tie_note}{biggest}')
    with right, st.expander("Show data: every inflection point for the plotted riders"):
        items = []
        if bibs:
            meta = selected.set_index("stage_no")
            for stage_no, group in inflections.groupby("stage_no", sort=True):
                s = meta.loc[stage_no]
                moves = []
                for r in group.itertuples():
                    arrow = '<span class="up">▲</span>' if r.gc_rank < r.prev_rank else '<span class="down">▼</span>'
                    takes = ", takes yellow" if r.takes_yellow else ""
                    moves.append(f"<b>{escape(r.rider_name)}</b> {r.prev_rank}→{r.gc_rank} {arrow} ({fmt.signed(r.delta_gap)}{takes})")
                items.append(
                    f'<div class="inf"><span><b style="display:flex;align-items:center;gap:6px"><i class="dot" style="background:{ui.TYPE_COLOURS[s.type]}"></i>Stage {stage_no}</b>'
                    f'<span class="note">{s.type_label} · {escape(s.route)}</span></span><span class="num">{" · ".join(moves)}</span></div>'
                )
        body = "".join(items) or '<div class="inf">No GC position changes for these riders.</div>'
        ui.html(f'<div class="eyebrow" style="margin-bottom:6px">Every inflection point for the plotted riders ({len(items)} stages)</div>'
                f'<div class="inf-list">{body}</div>'
                '<div class="note" style="margin-top:6px">Inflection = a stage where a plotted rider\'s GC rank differs from the previous selected stage. '
                'Bracket = change in gap to the leader that day (+ lost, − gained).</div>')

# ---------- Leaders, distance mix, exits ----------
left, middle, right = st.columns([4, 3, 3])
with left:
    with ui.card("leaders", "Classification leaders"):
        young = queries.young(f, state.get("w_yrule_value", "age"), f.cutoff)
        points = queries.derived(f, "points")
        kom = queries.derived(f, "kom")
        teams = queries.best_team(f)
        leader = final.iloc[0] if not final.empty else None

        def row(label, who, sub, stat, fill, stroke):
            return (f'<div class="leader">{ui.jersey(fill, stroke)}<div class="who"><span class="eyebrow">{label}</span><b style="font-size:15px">{escape(str(who))}</b>'
                    f'<span class="note">{escape(str(sub))}</span></div><span class="stat">{escape(str(stat))}</span></div>')

        html = ""
        html += row("General classification", leader.rider_name, leader.team, fmt.hms(leader.cum_time), "#F5C400", "#B58D00") if leader is not None else ""
        html += row("Points*", points.iloc[0].rider_name, points.iloc[0].team, f"{points.iloc[0].points} pts", "#1E8449", "#145C33") if not points.empty else ""
        html += row("King of the mountains*", kom.iloc[0].rider_name, kom.iloc[0].team, f"{kom.iloc[0].points} pts", "#FFFFFF", "#C62F36") if not kom.empty else ""
        html += row("Young rider", young.iloc[0].rider_name, young.iloc[0].team, f"GC {young.iloc[0].gc_rank} · {fmt.gap(young.iloc[0].gap_to_gc_leader)}", "#FFFFFF", "#5B6170") if not young.empty else ""
        if not teams.empty:
            margin = f"{fmt.gap(teams.iloc[1].gap)} on {teams.iloc[1].team}" if len(teams) > 1 else ""
            html += row("Best team (top-3 rule)", teams.iloc[0].team, "Sum of 3 fastest per stage", margin, "#15171C", "#15171C")
        ui.html(html)
        ui.note("*Derived from finishing positions, not the official scoring: the data has no intermediate sprints or categorised climbs. See About / Method.")
        st.page_link(ui.PAGES["gc"], label="Chapter 2: Our leader vs the rivals →")

with middle:
    with ui.card("mix", "Where the kilometres went"):
        mix = queries.type_mix(f)
        total = mix["km"].sum()
        segments = "".join(f'<div title="{r.type_label}" style="width:{r.km / total * 100:.1f}%;background:{ui.TYPE_COLOURS[r.type]}"></div>' for r in mix.itertuples())
        lines = "".join(
            f'<div class="num" style="display:flex;justify-content:space-between;border-bottom:1px solid #F0F1F4;padding:6px 0;font-size:14px">'
            f'<span style="display:flex;align-items:center;gap:8px"><i class="dot" style="background:{ui.TYPE_COLOURS[r.type]}"></i>{r.type_label} · {r.stages} stage{"s" if r.stages > 1 else ""}</span><b>{r.km:,.1f} km</b></div>'
            for r in mix.itertuples()
        )
        ui.html(f'<div style="display:flex;height:28px;border-radius:6px;overflow:hidden;margin-bottom:8px">{segments}</div>{lines}')

with right:
    with ui.card("exits", "Who left the race"):
        first, last = selected["stage_no"].min(), selected["stage_no"].max()
        exits = queries.exits()
        exits = exits[exits["stage_no"].between(first, last)]
        counts = exits["reason"].value_counts()
        if counts.empty:
            ui.note("No exits in this stage range.")
        else:
            ui.html("".join(
                f'<div class="hrow num" style="grid-template-columns:90px 1fr 28px"><span>{reason}</span>{ui.bar_html(n / counts.max() * 100)}<b style="text-align:right">{n}</b></div>'
                for reason, n in counts.items()
            ))
        ui.note("DNS = did not start that stage · Withdrawal = abandoned during it. These are the only two reasons in the data.")
        st.page_link(ui.PAGES["riders"], label="See the exit list →")
