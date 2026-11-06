"""Teams: E3 Best Team and who carried the time, E14 top-10 intensity, E13 squad depth."""
from html import escape

import pandas as pd
import streamlit as st

from lib import features, filters, queries, ui
from lib import format as fmt

state = st.session_state

team_list = queries.team_names()
team_country = dict(zip(team_list["name"], team_list["country"]))
crumb = state.get("w_team_sel") if features.on("E3") else None
ui.header(["Teams"] + ([crumb] if crumb else []), "Team performance")
f = filters.bar()
selected = queries.selected_stages(f)
best = queries.best_team(f)

# ---------- E3: Best team table (requirement c) and its drill-down, each with its own switch ----------
show_table, show_drill = features.on("Best team"), features.on("E3")
if show_drill and state.get("w_team_sel") not in team_country:
    state.w_team_sel = best.iloc[0].team if not best.empty else team_list.iloc[0]["name"]
# Without the drill-down, the table takes the full row
left, right = st.columns([3, 2]) if show_drill else (st.container(), None)

if show_table:
    with left:
        click_hint = " · click a team to drill down" if show_drill else ""
        with ui.card("best", "Best team classification", tag="Req. c · E3",
                     sub=f"Sum of each stage's 3 fastest riders (adjusted time), accumulated over the selected stages · bar = gap to the leading team{click_hint}"):
            show_all = st.toggle(f"Show all {len(best)} teams", key="w_bt_all") if len(best) > 10 else False
            shown = (best if show_all else best.head(10)).reset_index(drop=True)
            peak = max(shown["gap"].max(), 1) if not shown.empty else 1
            view = pd.DataFrame({
                "#": shown["team_rank"], "Team": shown["team"],
                "Gap bar": shown["gap"] / peak,
                "Time / gap": [fmt.hms(t) if g == 0 else fmt.gap(g) for t, g in zip(shown["total_time"], shown["gap"])],
            })
            leader_style = view.style.apply(lambda c: ["background-color:#FFF3BF;font-weight:700" if i == 0 else "" for i in range(len(c))], subset=["#", "Team"])
            event = ui.table(view, key="t_best", right=["Time / gap"], select="row" if show_drill else None, height=40 + 35 * len(view), styler=leader_style,
                             column_config={"Gap bar": st.column_config.ProgressColumn("Gap to leader", format=" ", min_value=0, max_value=1, color="#7C8291")})
            if show_drill:
                row = ui.new_row(event, "t_best")
                if row is not None:
                    state.w_team_sel = shown.iloc[row].team
                    st.rerun()
            ui.note(f"A team needs 3 finishers on every selected stage to be ranked{f' ({23 - len(best)} unranked)' if len(best) < 23 else ''}.")

# ---------- E3 drill-down: who carried the time (hidden unless switched on in lib/features.py) ----------
if show_drill:
    with right:
        team = state.w_team_sel
        depth = queries.squad_depth().set_index("team").loc[team]
        with ui.card("carry", escape(team), drill="Drill-down · who carried the time",
                     sub=f"{team_country[team]} · {depth.distinct_riders} riders started · {depth.finished} finished the race"):
            contribution = queries.team_contribution(f, team)
            stage_rows = queries.team_stage_rows(f, team)
            n_stages = len(selected)
            status = queries.roster(team).set_index("rider_bib")
            rows_html = ""
            for r in contribution.itertuples():
                counted = set(stage_rows.loc[(stage_rows["rider_bib"] == r.rider_bib) & stage_rows["counted"], "stage_no"])
                finished = set(stage_rows.loc[stage_rows["rider_bib"] == r.rider_bib, "stage_no"])
                cells = ""
                for s in selected.itertuples():
                    if s.stage_no in counted:
                        cells += f'<span class="sq" title="Stage {s.stage_no}: counted in the team top 3" style="height:12px;background:#2E5FA8;border-color:#2E5FA8"></span>'
                    elif s.stage_no in finished:
                        cells += f'<span class="sq" title="Stage {s.stage_no}: finished, not counted" style="height:12px"></span>'
                    else:
                        cells += f'<span class="sq" title="Stage {s.stage_no}: no result" style="height:12px;background:#F0F1F4;border-style:dashed"></span>'
                exit_note = ""
                if pd.notna(status.loc[r.rider_bib, "exit_stage"]):
                    exit_note = f' <span class="note">exit S{int(status.loc[r.rider_bib, "exit_stage"])}</span>'
                share = f"{r.share_pct:.1f}%" if pd.notna(r.share_pct) else "—"
                rows_html += (f'<div style="padding:6px 0;border-bottom:1px solid #F0F1F4"><div class="num" style="display:flex;justify-content:space-between;font-size:14px;margin-bottom:4px">'
                              f'<span><b>{escape(r.rider_name)}</b>{exit_note}</span><span>{r.stages_counted}/{n_stages} · {share}</span></div>'
                              f'<div class="strip" style="grid-template-columns:repeat({n_stages},minmax(0,1fr))">{cells}</div></div>')
            ui.html(f'<div class="eyebrow" style="display:flex;justify-content:space-between"><span>Rider</span><span>Stages counted · share of team time</span></div>{rows_html}')
            ui.note(f"Filled = counted in the team's top 3 that stage · outlined = finished, not counted · dashed = no result. {n_stages * 3} counted slots = {n_stages} stages × 3.")


# ---------- E14 top-10 intensity ----------
TYPE_COLUMNS = {"Flat": "flat", "Hilly": "hilly", "Mountain": "mountain", "ITT": "individual time-trial"}
SHADES = ["", "#E4ECF7", "#C9D9EF", "#9DB9E0", "#6F97D0", "#2E5FA8"]


def shade(value):
    level = min(5, (int(value) + 1) // 2)
    if not level:
        return ""
    colour = "color:#FFFFFF;" if level >= 4 else ""
    return f"background-color:{SHADES[level]};{colour}font-weight:700"


with ui.card("intensity", "Top-10 intensity by team", tag="E14", sub="Top-10 stage finishes (rank ≤ 10, finishing order) by stage type · click a stage-type cell for its stages and riders"):
    ui.html('<div class="callout"><b>How it is counted.</b> Every rider counts: two riders from one team in the same stage\'s top 10 add 2 to that team. '
            'The cell drill-down shows the stages and riders behind any number.</div>')
    top10 = queries.top10_by_team(f).reset_index(drop=True)
    present = [label for label, value in TYPE_COLUMNS.items() if value in set(selected["type"])]
    view = pd.DataFrame({"Team": top10["team"]})
    source = {"Flat": "flat", "Hilly": "hilly", "Mountain": "mountain", "ITT": "itt"}
    for label in present:
        view[label] = top10[source[label]]
    view["Total"] = top10["finishes"]
    left, right = st.columns([5, 4])
    with left:
        event = ui.table(view, key="t_intensity", select="cell", styler=view.style.map(shade, subset=present), height=38 + 35 * len(view))
        cell = ui.new_cell(event, "t_intensity")
        if cell is not None and cell[1] in present:
            state.w_cell = (top10.iloc[int(cell[0])].team, cell[1])
    with right:
        chosen = state.get("w_cell")
        with ui.card("cell", "Cell drill", drill="Stages and riders behind a cell"):
            if not chosen or chosen[1] not in present:
                ui.note("Click a Flat, Hilly, Mountain or ITT cell to list its stages and riders.")
            else:
                team_name, label = chosen
                rows = queries.top10_rows(f, team=team_name, stage_type=TYPE_COLUMNS[label])
                ui.html(f'<b>{escape(team_name)} × {label}: {len(rows)} finishes on {rows["stage_no"].nunique()} stages by {rows["rider_bib"].nunique()} riders</b>')
                if not rows.empty:
                    grouped = rows.groupby("stage_no", sort=True).agg(
                        route=("route", "first"), who=("rider_name", list), ranks=("rank", list)).reset_index()
                    detail = pd.DataFrame({
                        "Stage": "S" + grouped["stage_no"].astype(str),
                        "Riders (rank)": [", ".join(f"{n} ({r})" for n, r in zip(w, k)) for w, k in zip(grouped["who"], grouped["ranks"])],
                        "Counts": [len(w) for w in grouped["who"]],
                    })
                    ui.table(detail, height=min(38 + 35 * len(detail), 420))

# ---------- E13 squad depth ----------
if features.on("E13"):
    with ui.card("depth", "Squad depth", tag="E13", sub="Distinct riders per team · ● finished the race, ○ exited · click a team for its roster"):
        squads = queries.squad_depth().reset_index(drop=True)
        if squads["distinct_riders"].nunique() == 1:
            ui.html(f'<div class="callout">All {len(squads)} teams started {squads["distinct_riders"].iloc[0]} distinct riders, so no roster is broader than another; sorted by finishers instead.</div>')
        view = pd.DataFrame({
            "Team": squads["team"], "Country": squads["team_country"], "Distinct riders": squads["distinct_riders"],
            "Status": ["●" * n + "○" * x for n, x in zip(squads["finished"], squads["exited"])],
            "Finished": squads["finished"].astype(str) + "/" + squads["distinct_riders"].astype(str),
        })
        left, right = st.columns([3, 2])
        with left:
            event = ui.table(view, key="t_depth", right=["Finished"], select="row", height=38 + 35 * len(view))
            row = ui.new_row(event, "t_depth")
            if row is not None:
                state.w_roster = squads.iloc[row].team
        with right:
            roster_team = state.get("w_roster")
            with ui.card("roster", escape(roster_team) if roster_team else "Roster", drill="Drill-down · squad"):
                if not roster_team:
                    ui.note("Click a team to see its riders, nationalities and status.")
                else:
                    roster = queries.roster(roster_team)
                    ui.table(pd.DataFrame({
                        "#": roster["rider_bib"], "Rider": roster["rider_name"],
                        "Nationality": roster["rider_country_name"] + " (" + roster["rider_country"] + ")",
                        "Status": [s if s == "Finished" else f"{s} · stage {int(e)}" for s, e in zip(roster["status"], roster["exit_stage"].fillna(0))],
                    }), height=38 + 35 * len(roster))
