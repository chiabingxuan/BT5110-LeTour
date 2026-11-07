"""Chapter 4, Where we win and lose: E5 mountain contours scatter with a rider drill-down, E2 stage in focus
(top 10 as a lollipop and the squads that filled it, coloured by team), E11 time trials as a dot strip,
E15 the long day (hidden). The Time trials detail page keeps the full ITT results."""
from html import escape

import pandas as pd
import streamlit as st

from lib import charts, features, filters, queries, team, ui
from lib import format as fmt

state = st.session_state
state.setdefault("w_stage", 12)

ctx = team.context()
ui.header(["4 · Where we win and lose"], "Where do we win and lose?")
f = filters.bar()
all_stages = queries.stages()
selected = queries.selected_stages(f)
all_riders = queries.riders().set_index("rider_bib")

# ---------- E5 mountain contours: podiums against mean gap ----------
contours = queries.contours(f)
with ui.card("contours", "Who climbs with the best", tag="E5",
             sub="Riders who finished every selected mountain stage · podiums (rank ≤ 3) against mean gap to the stage winner · up and to the left is best"):
    if contours.empty:
        ui.note("No mountain stages or riders match the current filter.")
    else:
        ours = contours[contours["team"] == ctx.my].sort_values(["podiums", "mean_gap"], ascending=[False, True])
        rivals = contours[contours["team"].isin(ctx.rivals)].sort_values(["podiums", "mean_gap"], ascending=[False, True])
        if ours.empty:
            ui.takeaway(f"None of our riders finished every selected mountain stage.")
        else:
            o = ours.iloc[0]
            versus = (f"; the best rival climber, {escape(rivals.iloc[0].rider_name)}, has {rivals.iloc[0].podiums} with a mean gap of {fmt.gap(rivals.iloc[0].mean_gap)}"
                      if not rivals.empty else "")
            ui.takeaway(f"Our best climber, <b>{escape(o.rider_name)}</b>, took {o.podiums} mountain podium{'s' if o.podiums != 1 else ''} "
                        f"with a mean gap of {fmt.gap(o.mean_gap) if o.mean_gap else 'zero'}{versus}.")
        labelled = set(ours["rider_bib"].head(3)) | set(rivals["rider_bib"].head(len(ctx.rivals) + 1)) | set(contours["rider_bib"].head(3))
        left, right = st.columns([3, 2])
        with left:
            st.plotly_chart(charts.contour_scatter(contours, ctx, labelled), width="stretch", config={"displayModeBar": False}, key="contour_chart")
            ui.html(f"<div>{team.swatches(ctx)}</div>")
        with right:
            options = contours["rider_bib"].tolist()
            if state.get("w_mtn") not in options:
                state.w_mtn = int(ours.iloc[0].rider_bib) if not ours.empty else int(options[0])
            with ui.card("mtn", "Mountain stages, one by one", drill="Drill-down · rider"):
                st.selectbox("Rider", options, key="w_mtn",
                             format_func=lambda b: f"{all_riders.loc[b, 'rider_name']} · {all_riders.loc[b, 'team']}")
                c = contours[contours["rider_bib"] == state.w_mtn].iloc[0]
                daily = queries.rider_results(f, state.w_mtn)
                daily = daily[daily["type"] == "mountain"]
                ui.note(f"{c.podiums} podium{'' if c.podiums == 1 else 's'} from {c.stages} mountain stage{'' if c.stages == 1 else 's'} · "
                        f"mean gap {fmt.gap(c.mean_gap)} · bar = gap to the stage winner, label = finishing rank")
                st.plotly_chart(charts.v_bars([f"S{n}" for n in daily["stage_no"]], list(daily["gap_to_winner"]), "#B5644A",
                                              [f"{r} ◆" if r <= 3 else str(r) for r in daily["rank"]], height=190),
                                width="stretch", config={"displayModeBar": False}, key="mtn_chart")
                with st.expander("Show data"):
                    view = pd.DataFrame({
                        "Stage": "S" + daily["stage_no"].astype(str) + " · " + daily["route"],
                        "Rank": [f"{r} ◆" if r <= 3 else str(r) for r in daily["rank"]],
                        "Adj. time": daily["adjusted_time"].map(fmt.hms), "Gap to winner": daily["gap_to_winner"].map(fmt.gap),
                    }).reset_index(drop=True)
                    event = ui.table(view, key="t_mtn_daily", right=["Rank", "Adj. time", "Gap to winner"], select="row")
                    row = ui.new_row(event, "t_mtn_daily")
                    if row is not None:
                        state.w_stage = int(daily.iloc[row].stage_no)
                        st.rerun()
                    ui.note("◆ = podium. Click a row to open that stage below.")

with ui.card("picker", "Stage in focus: choose a stage", "Colour = stage type · faded = outside the current filter", tag="E2"):
    ui.stage_button_css(all_stages, "pick_", selected=state.w_stage, selected_only_in=set(selected["stage_no"]))
    columns = st.columns(21, gap=None)
    for column, row in zip(columns, all_stages.itertuples()):
        if column.button(str(row.stage_no), key=f"pick_{row.stage_no}", help=row.stage_label, width="stretch"):
            state.w_stage = row.stage_no
            st.rerun()

stage = all_stages[all_stages["stage_no"] == state.w_stage].iloc[0]
ui.html(f"""
<section class="banner" aria-label="Stage banner">
  <div class="l">
    <span style="display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;letter-spacing:.06em;color:#E8D9D2"><i class="dot" style="background:{ui.TYPE_COLOURS[stage.type]}"></i>{stage.type_label.upper()} · {fmt.long_date(stage.date).upper()}</span>
    <span class="t">Stage {stage.stage_no} · {escape(stage.route)}</span>
    <span style="color:#C9CCD3">Start {stage.start_country} · Finish {stage.end_country}</span>
  </div>
  <div class="stats">
    <div><span class="eyebrow">Distance</span><span class="big">{stage.dist_km:.1f} km</span></div>
    <div><span class="eyebrow">Winner</span><b style="font-size:17px">{escape(stage.winner_name)}</b><span class="num" style="color:#C9CCD3;font-size:13px">{fmt.hms(stage.winner_time)}</span></div>
    <div><span class="eyebrow">Winner's avg speed</span><span class="big">{stage.winner_speed_kmh:.1f} km/h</span></div>
  </div>
</section>
""")

top = queries.stage_results(state.w_stage, 10)
ours = top[top["team"] == ctx.my]
if ours.empty:
    ui.takeaway(f"None of our riders made the top 10 on stage {stage.stage_no}; {escape(stage.winner_name)} won it.")
else:
    best = ours.iloc[0]
    ui.takeaway(f"We placed {len(ours)} rider{'s' if len(ours) != 1 else ''} in the top 10 on stage {stage.stage_no}; "
                + (f"<b>{escape(best.rider_name)}</b> won it." if best["rank"] == 1 else
                   f"best was <b>{escape(best.rider_name)}</b>, {fmt.ordinal(best['rank'])} at {fmt.gap(best.gap_to_winner) if best.gap_to_winner else 'the same time'}."))
left, right = st.columns([3, 2])
with left:
    with ui.card("top10", "Top 10 finishers", tag="E2", sub="Podium and chasers coloured by team · grey = other teams · chasers' dot = gap to the stage winner"):
        podium = pd.DataFrame({"rank": top["rank"], "rider_name": top["rider_name"], "team": top["team"], "gap": top["gap_to_winner"]}).head(3)
        st.plotly_chart(charts.podium(podium, ctx), width="stretch", config={"displayModeBar": False}, key="podium_chart")
        chasers = top[top["rank"] > 3]
        if not chasers.empty:
            ui.html('<div class="eyebrow" style="margin:4px 0 2px">The chasing group</div>')
            rows = pd.DataFrame({"label": [f"{r}. {n}" for r, n in zip(chasers["rank"], chasers["rider_name"])],
                                 "team": chasers["team"], "gap": chasers["gap_to_winner"]})
            st.plotly_chart(charts.lollipop(rows, ctx), width="stretch", config={"displayModeBar": False}, key="top10_chart")
        with st.expander("Show data: top 10 table (click a row to open the rider)"):
            view = pd.DataFrame({
                "#": top["rank"], "Rider": top["rider_name"], "Team": top["team"], "Nat.": top["rider_country"],
                "Adjusted time": top["adjusted_time"].map(fmt.hms), "Gap": top["gap_to_winner"].map(fmt.gap),
                "Bonus": top["time_bonus"].map(fmt.bonus),
            })
            event = ui.table(view, key="t_stage_top", right=["Adjusted time", "Gap", "Bonus"], select="row")
            row = ui.new_row(event, "t_stage_top")
            if row is not None:
                ui.goto("riders", w_rider=int(top.iloc[row].rider_bib))
            ui.note("Order = finishing rank; riders on the same time keep the order they crossed the line.")
with right:
    with ui.card("squads", "Which squads filled the top 10", tag="E2", sub="Riders in the stage top 10 per team"):
        counts = top["team"].value_counts()
        st.plotly_chart(charts.h_bars(list(counts.index), [int(v) for v in counts.values],
                                      [ctx.colour(t) if ctx.is_focus(t) else "#9AA0AC" for t in counts.index], height=30 * len(counts) + 20),
                        width="stretch", config={"displayModeBar": False}, key="squads_chart")

# ---------- E11 against the clock ----------
itts = all_stages[all_stages["type"] == "individual time-trial"]
with ui.card("itt", "Against the clock", tag="E11",
             sub=f"{len(itts)} time trials · {itts['dist_km'].sum():.1f} km · every finisher is a dot at their gap to the winner · hover for names"):
    results = pd.concat([queries.stage_results(n) for n in itts["stage_no"]], ignore_index=True)
    ours = results[results["team"] == ctx.my].sort_values("rank").groupby("stage_no").head(1).sort_values("stage_no")
    if ours.empty:
        ui.takeaway("None of our riders finished a time trial.")
    else:
        ui.takeaway("Our best against the clock: " + "; ".join(
            f"stage {r.stage_no}, <b>{escape(r.rider_name)}</b> {'won' if r.rank == 1 else fmt.ordinal(r.rank) + ' at ' + fmt.gap(r.gap_to_winner)}"
            for r in ours.itertuples()) + ".")
    labelled = set(ours["rider_bib"]) | set(results[results["team"].isin(ctx.rivals)].sort_values("rank").groupby("stage_no").head(1)["rider_bib"])
    st.plotly_chart(charts.itt_strip(results, itts, ctx, labelled), width="stretch", config={"displayModeBar": False}, key="itt_chart")
    ui.note("Labels = each winner, our best rider and the best rival rider on each time trial (rank in brackets).")
    st.page_link(ui.PAGES["time_trials"], label="Open the Time trials detail page: full results and what each did to the GC →")

# ---------- E15 the long day (hidden unless switched on in lib/features.py) ----------
if features.on("E15"):
    longest_first = selected.sort_values(["dist_km", "stage_no"], ascending=[False, True])
    longest = longest_first.iloc[0]
    left, right = st.columns([3, 2])
    with left:
        with ui.card("longday", "The long day", tag="E15", sub="Selected stages sorted by distance · longest outlined · open any stage with the picker above"):
            labels = [f"S{r.stage_no} · {r.route}" for r in longest_first.itertuples()]
            fig = charts.h_bars(labels, list(longest_first["dist_km"]), [ui.TYPE_COLOURS[t] for t in longest_first["type"]],
                                texts=[f"{d:.1f}" for d in longest_first["dist_km"]], height=26 * len(labels) + 20)
            fig.update_traces(marker_line_width=[2.5] + [0] * (len(labels) - 1), marker_line_color="#15171C")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, key="longday_chart")
    with right:
        with ui.card("spotlight", "Spotlight · longest stage", tag="E15"):
            ui.html(f"""<div style="display:flex;gap:12px;align-items:center"><span style="width:52px;height:52px;flex:none;border-radius:10px;background:{ui.TYPE_COLOURS[longest.type]};color:{ui.TYPE_FG[longest.type]};display:flex;align-items:center;justify-content:center;font-family:'Barlow Condensed';font-weight:700;font-size:26px">{longest.stage_no}</span>
            <span><b style="font-size:17px">{escape(longest.route)}</b><br><span class="note">{longest.type_label} · {fmt.long_date(longest.date)} · {longest.dist_km:.1f} km</span></span></div>""")
            leaders = queries.stage_results(longest.stage_no, 5)
            ui.table(pd.DataFrame({
                "#": leaders["rank"], "Rider": leaders["rider_name"], "Adjusted time": leaders["adjusted_time"].map(fmt.hms),
                "Gap": leaders["gap_to_winner"].map(fmt.gap),
            }), right=["Adjusted time", "Gap"])
            ui.note("Adjusted time includes time bonuses and penalties.")
