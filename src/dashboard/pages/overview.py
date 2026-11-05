"""Overview: KPIs, route strip, E10 GC storyline with inflection points, leaders, distance mix and exits."""
from html import escape

import streamlit as st

from lib import charts, filters, queries, ui
from lib import format as fmt

state = st.session_state

ui.header([], "Race overview")
f = filters.bar(young=True)
selected = queries.selected_stages(f)
final = queries.gc_final(f)

# ---------- KPI tiles ----------
k = queries.kpis(f)
ui.kpi_tiles([
    ("Stages", int(k.stages), f"{int(k.itt_stages)} individual time-trial{'' if k.itt_stages == 1 else 's'}"),
    ("Distance", f"{k.km:,.0f}", "km raced"),
    ("Starters", int(k.starters), "riders still in at the first selected stage"),
    ("Finishers", int(k.finishers), f"{int(k.exits)} exits in range"),
    ("Nations", int(k.nations), "by rider nationality"),
    ("Winning margin", fmt.gap(k.margin).lstrip("+"), "GC 1st → 2nd"),
])

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


with ui.card("story", "GC storyline", tag="E10",
             sub="Riders are plotted over the selected stages · shaded = mountain stages · numbered flags = yellow jersey changes"):
    # Finishers in GC order, then riders who left the race and so have no final rank
    top5 = final["rider_bib"].head(5).tolist()
    in_gc = set(queries.gc_by_stage(f)["rider_bib"])
    all_riders = queries.riders().set_index("rider_bib")
    left = sorted((b for b in in_gc if b not in set(final["rider_bib"])), key=lambda b: all_riders.loc[b, "rider_name"])
    names = dict(zip(final["rider_bib"], final["gc_rank"].astype(str) + ". " + final["rider_name"]))
    names.update({b: f"{all_riders.loc[b, 'rider_name']} (left at stage {int(all_riders.loc[b, 'exit_stage'])})" for b in left})
    pickable = all_riders.loc[list(names)].reset_index()
    valid = set(names)
    state.w_story = [b for b in state.get("w_story", top5) if b in valid] or top5

    c1, c2, c3 = st.columns([5, 2, 1.1], vertical_alignment="bottom")
    c1.multiselect("Riders on the chart (default: GC top 5; search any rider, including those who left the race)", list(names), key="w_story", format_func=names.get, max_selections=10)
    c2.selectbox("Add a team's riders", queries.team_names()["name"].tolist(), key="add_team", index=None,
                 placeholder="Choose team…", on_change=add_team_riders, args=(pickable,))
    c3.button("Reset to top 5", on_click=reset_story, args=(top5,), width="stretch")

    state.setdefault("w_story_view", "GC rank")
    if not state.w_story_view:
        state.w_story_view = "GC rank"
    st.segmented_control("Measure", ["GC rank", "Cumulative time"], key="w_story_view", label_visibility="collapsed")
    measure = "rank" if state.w_story_view == "GC rank" else "time"

    bibs = state.w_story
    gc = queries.gc_by_stage(f, bibs) if bibs else None
    inflections = queries.inflections(f, bibs) if bibs else None
    yellow = queries.yellow(f)
    if bibs:
        exits = {b: int(all_riders.loc[b, "exit_stage"]) for b in bibs if b in left}
        st.plotly_chart(charts.gc_lines(gc, selected, bibs, measure, inflections, yellow, exits=exits), width="stretch", config={"displayModeBar": False}, key="story_chart")
        legend = "".join(
            f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:16px"><i style="width:18px;height:3px;background:{charts.RIDER_LINES[i % 10]};display:inline-block"></i>{escape(all_riders.loc[b, "rider_name"])}</span>'
            for i, b in enumerate(bibs)
        )
        ui.html(f'<div style="font-size:13px">{legend}</div>')
    ui.note(("Overall GC position after each stage, 1 at the top; crossings are reshuffles; ranks below 20 are drawn at 20+."
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
    with right:
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
        st.page_link(ui.PAGES["gc"], label="Open GC & Classifications →")

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
