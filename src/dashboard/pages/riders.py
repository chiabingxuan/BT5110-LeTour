"""Riders: profile and daily trace, E5 mountain contours with drill-down, E6 speed by terrain, E12 consistency, exits."""
from html import escape

import pandas as pd
import streamlit as st

from lib import charts, filters, queries, ui
from lib import format as fmt

state = st.session_state

all_riders = queries.riders().set_index("rider_bib")
state.setdefault("w_rider", 1)
if state.w_rider not in all_riders.index:
    state.w_rider = 1

ui.header(["Riders", all_riders.loc[state.w_rider, "rider_name"]], "Rider performance")
f = filters.bar()
selected = queries.selected_stages(f)
final = queries.gc_final(f)
gc_rank = dict(zip(final["rider_bib"], final["gc_rank"]))

# ---------- Rider selector and facts ----------
finishers = f.narrow(final)["rider_bib"].tolist()
others = sorted((b for b in f.narrow(all_riders.reset_index())["rider_bib"] if b not in gc_rank), key=lambda b: all_riders.loc[b, "rider_name"])
options = finishers + others
if state.w_rider not in options:
    options = [state.w_rider] + options


def rider_label(bib):
    rider = all_riders.loc[bib]
    if bib in gc_rank:
        return f"{gc_rank[bib]}. {rider.rider_name}"
    return f"{rider.rider_name}" + (f" (exit stage {int(rider.exit_stage)})" if pd.notna(rider.exit_stage) else " (not ranked)")


with st.container(key="card_rider"):
    c1, c2 = st.columns([2, 5], vertical_alignment="bottom")
    c1.selectbox("Rider (finishers in GC order, then the rest)", options, key="w_rider", format_func=rider_label)
    rider = all_riders.loc[state.w_rider]
    results = queries.rider_results(f, state.w_rider)
    wins = int((results["rank"] == 1).sum())
    total_bonus = results["time_bonus"].sum()
    if state.w_rider in gc_rank:
        standing = fmt.ordinal(gc_rank[state.w_rider])
    elif pd.notna(rider.exit_stage):
        standing = f"DNF – stage {int(rider.exit_stage)} ({rider.exit_reason})"
    else:
        standing = "Not ranked"
    facts = [("Team", rider.team), ("Nation", f"{rider.rider_country_name} ({rider.rider_country})"), ("Age at start", rider.age_at_start),
             ("GC", standing), ("Stage wins", wins), ("Bonuses", fmt.bonus(total_bonus))]
    c2.html('<div style="display:flex;flex-wrap:wrap;gap:24px;padding-bottom:4px">' + "".join(
        f'<div style="display:flex;flex-direction:column;gap:2px"><span class="eyebrow">{label}</span><b class="num" style="font-size:17px">{escape(str(value))}</b></div>'
        for label, value in facts) + "</div>")

# ---------- Daily trace ----------
with ui.card("trace", "Daily trace · stage finishing rank"):
    state.setdefault("w_trace", "All stages")
    if not state.w_trace:
        state.w_trace = "All stages"
    st.segmented_control("Stages shown", ["All stages", "Mountain stages only"], key="w_trace", label_visibility="collapsed")
    mountain_only = state.w_trace == "Mountain stages only"
    shown = selected[selected["type"] == "mountain"] if mountain_only else selected
    if shown.empty:
        ui.note("No mountain stages in the current filter.")
    else:
        by_stage = results.set_index("stage_no")
        rules = []
        columns = st.columns(len(shown), gap=None) if len(shown) > 8 else st.columns(max(len(shown), 8))
        for column, row in zip(columns, shown.itertuples()):
            has = row.stage_no in by_stage.index
            rank = int(by_stage.loc[row.stage_no, "rank"]) if has else "—"
            extra = f" {fmt.gap(by_stage.loc[row.stage_no, 'gap_to_winner'])}" if has and mountain_only else ""
            rules.append(f".st-key-trace_{row.stage_no} button{{border:0;border-top:4px solid {ui.TYPE_COLOURS[row.type]};border-radius:6px;background:#F7F8FA;min-height:58px;padding:4px 0}}")
            if has and rank == 1:
                rules.append(f".st-key-trace_{row.stage_no} button p{{color:#9A7400}}")
            if column.button(f"S{row.stage_no} **{rank}**{extra}", key=f"trace_{row.stage_no}", help=row.stage_label, width="stretch"):
                ui.goto("stages", w_stage=row.stage_no)
        ui.html("<style>" + "".join(rules) + "</style>")
        ui.note("Gold = stage win" + (" · last line = gap to the stage winner" if mountain_only else "") + " · click a stage to open it.")

# ---------- E5 mountain contours with drill-down ----------
contours = f.narrow(queries.contours(f))
left, right = st.columns(2)
with left:
    with ui.card("contours", "Mountain contours", tag="E5",
                 sub="Riders who finished every selected mountain stage · podiums (rank ≤ 3) · mean gap to the stage winner · click a row to drill down"):
        if contours.empty:
            ui.note("No mountain stages or riders match the current filter.")
        else:
            top = contours.head(12).reset_index(drop=True)
            peak = max(top["mean_gap"].max(), 1)
            view = pd.DataFrame({
                "Rider": top["rider_name"], "Mtn podiums": top["podiums"], "Mean gap": top["mean_gap"].map(fmt.gap),
                "": top["mean_gap"] / peak,
            })
            event = ui.table(view, key="t_contours", right=["Mean gap"], select="row",
                             column_config={"": st.column_config.ProgressColumn("", format=" ", min_value=0, max_value=1, color="#B5644A")})
            row = ui.new_row(event, "t_contours")
            if row is not None:
                state._pending = {"w_mtn": int(top.iloc[row].rider_bib), "w_rider": int(top.iloc[row].rider_bib), "w_trace": "Mountain stages only"}
                st.rerun()
with right:
    if not contours.empty:
        if state.get("w_mtn") not in contours["rider_bib"].tolist():
            state.w_mtn = int(state.w_rider) if state.w_rider in contours["rider_bib"].tolist() else int(contours.iloc[0].rider_bib)
        c = contours[contours["rider_bib"] == state.w_mtn].iloc[0]
        with ui.card("mtn", escape(c.rider_name), drill="Drill-down · mountain stages",
                     sub=f"{c.podiums} podium{'' if c.podiums == 1 else 's'} from {c.stages} mountain stage{'' if c.stages == 1 else 's'} · mean gap {fmt.gap(c.mean_gap)}"):
            daily = queries.rider_results(f, state.w_mtn)
            daily = daily[daily["type"] == "mountain"]
            st.plotly_chart(charts.v_bars([f"S{n}" for n in daily["stage_no"]], list(daily["gap_to_winner"]), "#B5644A",
                                          [fmt.gap(g) for g in daily["gap_to_winner"]], height=170),
                            width="stretch", config={"displayModeBar": False}, key="mtn_chart")
            view = pd.DataFrame({
                "Stage": "S" + daily["stage_no"].astype(str) + " · " + daily["route"],
                "Date": daily["date"].map(fmt.short_date),
                "Rank": [f"{r} ◆" if r <= 3 else str(r) for r in daily["rank"]],
                "Adj. time": daily["adjusted_time"].map(fmt.hms),
                "Gap to winner": daily["gap_to_winner"].map(fmt.gap),
            }).reset_index(drop=True)
            event = ui.table(view, key="t_mtn_daily", right=["Rank", "Adj. time", "Gap to winner"], select="row")
            row = ui.new_row(event, "t_mtn_daily")
            if row is not None:
                ui.goto("stages", w_stage=int(daily.iloc[row].stage_no))
            ui.note("◆ = podium. Click a row to open that stage in Stage in focus.")

# ---------- E6 speed by terrain ----------
speed = queries.speed_by_type(f)
medians = dict(speed.groupby("type")["median_speed"].first())
left, right = st.columns(2)
with left:
    with ui.card("speed", "Speed by terrain", tag="E6", sub="Average speed = distance ÷ adjusted time · selected rider or team vs the peloton median"):
        state.setdefault("w_grain", "Rider")
        if not state.w_grain:
            state.w_grain = "Rider"
        c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
        c1.segmented_control("Show", ["Rider", "Team"], key="w_grain")
        if state.w_grain == "Team":
            teams = queries.team_names()["name"].tolist()
            if state.get("w_speed_team") not in teams:
                state.w_speed_team = rider.team
            c2.selectbox("Team", teams, key="w_speed_team")
            subject = speed[speed["team"] == state.w_speed_team].groupby("type")["avg_speed"].mean().to_dict()
            name = state.w_speed_team
        else:
            subject = speed[speed["rider_bib"] == state.w_rider].set_index("type")["avg_speed"].to_dict()
            name = rider.rider_name
        st.plotly_chart(charts.speed_bars(subject, medians, name), width="stretch", config={"displayModeBar": False}, key="speed_chart")
        ui.note(f"Coloured = {escape(name)} · grey = peloton median · the axis starts at 25 km/h.")
with right:
    with ui.card("gainers", "Biggest gainers when the road turns mountainous", tag="E6",
                 sub="Gain = (mountain speed ÷ median) − (flat and hilly speed ÷ median)"):
        state.setdefault("w_gain_view", "Riders")
        if not state.w_gain_view:
            state.w_gain_view = "Riders"
        st.segmented_control("Gainers", ["Riders", "Teams"], key="w_gain_view", label_visibility="collapsed")
        if state.w_gain_view == "Riders":
            g = f.narrow(queries.gainers_riders(f).merge(all_riders[["rider_country"]], left_on="rider_bib", right_index=True)).head(10)
            view = pd.DataFrame({"Rider": g["rider_name"], "Team": g["team"], "Gain": g["gain_pct"].map("{:+.1f}%".format)})
        else:
            g = queries.gainers_teams(f).head(10)
            view = pd.DataFrame({"Team": g["team"], "Gain": g["gain_pct"].map("{:+.1f}%".format)})
        if view.empty:
            ui.note("Needs mountain and flat or hilly stages in the filter.")
        else:
            ui.table(view, right=["Gain"])

# ---------- E12 consistency and exits ----------
left, right = st.columns([3, 2])
with left:
    with ui.card("consistency", "Consistency near the front", tag="E12",
                 sub="Top-10 stage finishes in the selection · each square is a stage, filled in type colour with the rank"):
        leaders = f.narrow(queries.top10_riders(f))
        leaders = leaders.assign(gc=leaders["rider_bib"].map(gc_rank).fillna(999)).sort_values(["finishes", "gc"], ascending=[False, True]).head(10)
        rows = queries.top10_rows(f, leaders["rider_bib"].tolist()) if not leaders.empty else pd.DataFrame()
        html = ""
        for r in leaders.itertuples():
            ranks = dict(zip(rows.loc[rows["rider_bib"] == r.rider_bib, "stage_no"], rows.loc[rows["rider_bib"] == r.rider_bib, "rank"]))
            cells = ""
            for s in selected.itertuples():
                if s.stage_no in ranks:
                    cells += (f'<span class="sq" title="Stage {s.stage_no} · {s.type_label} · rank {ranks[s.stage_no]}" '
                              f'style="background:{ui.TYPE_COLOURS[s.type]};border-color:{ui.TYPE_COLOURS[s.type]};color:{ui.TYPE_FG[s.type]}">{ranks[s.stage_no]}</span>')
                else:
                    cells += f'<span class="sq" title="Stage {s.stage_no} · {s.type_label} · outside the top 10"></span>'
            html += (f'<div class="hrow" style="grid-template-columns:minmax(0,160px) 30px 1fr"><b style="font-size:14px">{escape(r.rider_name)}</b>'
                     f'<b class="num" style="font-family:\'Barlow Condensed\';font-size:22px">{r.finishes}</b>'
                     f'<div class="strip" style="grid-template-columns:repeat({len(selected)},minmax(0,1fr))">{cells}</div></div>')
        ui.html(html or '<div class="note">No top-10 finishes match the current filter.</div>')
        if not leaders.empty:
            with st.expander("Contributing stages"):
                bibs = leaders["rider_bib"].tolist()
                if state.get("w_cons") not in bibs:
                    state.w_cons = bibs[0]
                st.selectbox("Rider", bibs, key="w_cons", format_func=lambda b: all_riders.loc[b, "rider_name"])
                detail = rows[rows["rider_bib"] == state.w_cons]
                ui.table(pd.DataFrame({"Stage": detail["stage_no"].map("S{}".format) + " · " + detail["route"], "Type": detail["type_label"], "Rank": detail["rank"]}))
with right:
    with ui.card("race_exits", "Race exits"):
        exits = f.narrow(queries.exits())
        ui.table(pd.DataFrame({"Rider": exits["rider_name"], "Stage": exits["stage_no"], "Reason": exits["reason"]}), height=min(38 + 35 * len(exits), 380))
        ui.note(f"{len(exits)} of 24 · DNS = did not start that stage · Withdrawal = abandoned during it. No results exist from the exit stage onwards.")
