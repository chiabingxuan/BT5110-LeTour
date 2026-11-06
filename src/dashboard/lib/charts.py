"""Plotly charts. Stage-type colours come from ui.TYPE_COLOURS so each type looks the same everywhere."""
import math

import plotly.graph_objects as go

from lib import format as fmt
from lib.ui import TYPE_COLOURS, TYPE_LABELS

RIDER_LINES = ["#D4A200", "#2E5FA8", "#C0392B", "#17866A", "#7A5CC2", "#D9701E", "#2A9DB5", "#8C5A3C", "#5B6170", "#C2408E"]
MOUNTAIN_BAND = "#F6EBE6"
FONT = dict(family="Barlow, system-ui, sans-serif", size=13, color="#15171C")
RANK_TICKS = [1, 2, 3, 5, 10, 20, 50, 100, 150]


def base_layout(fig, height, **kwargs):
    fig.update_layout(
        height=height, font=FONT, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF",
        margin=dict(l=48, r=12, t=30, b=40), showlegend=False, hoverlabel=dict(font=FONT, bgcolor="#FFFFFF"), **kwargs,
    )
    return fig


def _stage_axis(fig, stages):
    """X axis over the selected stages; tick labels take the stage-type colour, mountain stages are shaded."""
    labels = [
        f'<span style="color:{TYPE_COLOURS[t]};font-weight:700">{n}</span>'
        for n, t in zip(stages["stage_no"], stages["type"])
    ]
    fig.update_xaxes(tickmode="array", tickvals=list(stages["seq"]), ticktext=labels, title="Stage",
                     range=[0.5, len(stages) + 0.5], showgrid=False, fixedrange=True)
    for seq, stage_type in zip(stages["seq"], stages["type"]):
        if stage_type == "mountain":
            fig.add_vrect(x0=seq - 0.5, x1=seq + 0.5, fillcolor=MOUNTAIN_BAND, line_width=0, layer="below")


def gc_lines(gc, stages, bibs, measure="rank", inflections=None, yellow=None, pivots=None, focus=None, exits=None, height=380,
             rank_scale="log", colours=None, bold=(), end_labels=None):
    """GC storyline (E10) and GC standing (E1). measure: 'rank' or 'time' (gap to the leader).
    rank_scale: 'log' or 'linear' spacing of the rank axis.
    exits maps a bib to its exit stage, for riders who left the race: their line ends in an ×.
    colours maps a bib to its line colour (by team role); bold bibs are drawn thicker;
    end_labels maps a bib to the label written at the end of its line.
    The inverted y axis puts the leader on top in both views."""
    fig = go.Figure()

    def colour_of(bib):
        if colours and bib in colours:
            return colours[bib]
        return RIDER_LINES[bibs.index(bib) % len(RIDER_LINES)]

    _stage_axis(fig, stages)
    seq_label = dict(zip(stages["seq"], stages["route"]))
    stage_of = dict(zip(stages["stage_no"], stages["seq"]))

    def y_value(row_rank, row_gap):
        return row_rank if measure == "rank" else row_gap / 60

    positions = {}
    hover_of = {}  # (bib, stage) -> full hover text, so a marker on top of a line loses nothing
    for i, bib in reversed(list(enumerate(bibs))):
        rows = gc[gc["rider_bib"] == bib].sort_values("seq")
        if rows.empty:
            continue
        ys = [y_value(r, g) for r, g in zip(rows["gc_rank"], rows["gap"])]
        positions[bib] = dict(zip(rows["stage_no"], ys))
        hover = [
            f"<b>{name}</b><br>Stage {stage}: {seq_label[seq]}<br>GC {rank} · {fmt.gap(gap) if gap else 'leader'}<br>Total {fmt.hms(cum)}"
            for name, stage, seq, rank, gap, cum in zip(
                rows["rider_name"], rows["stage_no"], rows["seq"], rows["gc_rank"], rows["gap"], rows["cum_time"])
        ]
        hover_of.update({(bib, stage): text for stage, text in zip(rows["stage_no"], hover)})
        if colours:
            width = 4.5 if bib == focus else (3.4 if bib in bold else 1.8)
        else:
            width = 4.5 if bib == focus else (3.2 if i == 0 and focus is None else 2.2)
        fig.add_trace(go.Scatter(
            x=rows["seq"], y=ys, mode="lines", name=rows["rider_name"].iloc[0],
            line=dict(color=colour_of(bib), width=width),
            hovertext=hover, hoverinfo="text",
        ))

    if inflections is not None and not inflections.empty:
        for takes, size in ((False, 9), (True, 15)):
            part = inflections[inflections["takes_yellow"] == takes]
            xs, ys, text, rings = [], [], [], []
            for row in part.itertuples():
                if row.rider_bib in positions and row.stage_no in positions[row.rider_bib]:
                    xs.append(stage_of[row.stage_no])
                    ys.append(positions[row.rider_bib][row.stage_no])
                    change = f"GC {row.prev_rank} → {row.gc_rank}" + (" · takes yellow" if row.takes_yellow else "")
                    text.append(f"{hover_of[(row.rider_bib, row.stage_no)]}<br>{change}")
                    rings.append(colour_of(row.rider_bib))
            if xs:
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="markers", hovertext=text, hoverinfo="text",
                    marker=dict(size=size, color="#F5C400" if takes else "#FFFFFF",
                                line=dict(width=2, color="#15171C" if takes else rings)),
                ))

    if pivots is not None and not pivots.empty:
        for row in pivots.itertuples():
            if row.rider_bib in positions and row.stage_no in positions[row.rider_bib]:
                fig.add_trace(go.Scatter(
                    x=[stage_of[row.stage_no]], y=[positions[row.rider_bib][row.stage_no]], mode="markers",
                    hovertext=[f"{hover_of[(row.rider_bib, row.stage_no)]}<br><b>Pivotal stage</b>"], hoverinfo="text",
                    marker=dict(symbol="diamond", size=13, color="#15171C",
                                line=dict(width=2, color=colour_of(row.rider_bib))),
                ))

    for bib, exit_stage in (exits or {}).items():
        if bib in positions:
            last = max(positions[bib])
            fig.add_trace(go.Scatter(
                x=[stage_of[last]], y=[positions[bib][last]], mode="markers",
                hovertext=[f"{hover_of[(bib, last)]}<br>Left the race at stage {exit_stage}"], hoverinfo="text",
                marker=dict(symbol="x", size=11, color=colour_of(bib), line=dict(width=1, color="#15171C")),
            ))

    for bib, label in (end_labels or {}).items():
        if bib in positions:
            last = max(positions[bib])
            y = positions[bib][last]
            # Annotations on a log axis are placed in log10 units
            y = math.log10(y) if measure == "rank" and rank_scale == "log" else y
            fig.add_annotation(x=stage_of[last], y=y, text=label, showarrow=False, xanchor="left", xshift=8,
                               font=dict(size=12, color=colour_of(bib)))
    if end_labels:
        fig.update_xaxes(range=[0.5, len(stages) + 0.5 + max(2.0, len(stages) * 0.16)])

    if yellow is not None:
        for row in yellow[yellow["is_change"]].itertuples():
            fig.add_annotation(
                x=row.seq, y=1.02, yref="paper", yanchor="bottom", showarrow=False, text=f"<b>{row.change_no}</b>",
                bgcolor="#F5C400", font=dict(color="#15171C", size=12), borderpad=3,
                hovertext=f"Stage {row.stage_no}: {row.holder_name} takes yellow",
            )

    if measure == "rank" and rank_scale == "log":
        # Every rank is shown. A log scale keeps the fight for the top places readable even when a
        # plotted rider sits far down the field: 1st to 10th gets about as much room as 10th to 100th.
        lowest = max((max(v.values()) for v in positions.values()), default=10)
        ticks = [t for t in RANK_TICKS if t <= max(lowest, 10)]
        if lowest > ticks[-1] * 1.3:
            ticks.append(int(lowest))  # label the lowest plotted rank too, e.g. 80 after 50
        fig.update_yaxes(title="GC position", type="log", autorange=False,
                         range=[math.log10(max(lowest, 10) * 1.15), math.log10(0.85)],
                         tickvals=ticks, ticktext=[str(t) for t in ticks],
                         gridcolor="#EEF0F3", griddash="dash", zeroline=False, fixedrange=True)
    elif measure == "rank":
        # Evenly spaced ranks, so distance on the chart is distance in the standings
        lowest = max((max(v.values()) for v in positions.values()), default=10)
        step = next(s for s in (1, 2, 5, 10, 20, 25, 50) if lowest / s <= 10)
        ticks = [1] + list(range(step, int(lowest) + 1, step))
        fig.update_yaxes(title="GC position", type="linear", autorange=False,
                         range=[max(lowest, 5) + 0.5 + lowest * 0.03, 0.5],
                         tickvals=ticks, ticktext=[str(t) for t in ticks],
                         gridcolor="#EEF0F3", griddash="dash", zeroline=False, fixedrange=True)
    else:
        top = max((max(v.values()) for v in positions.values()), default=1)
        fig.update_yaxes(title="Minutes behind the leader", autorange=False, range=[top * 1.05 + 0.2, -0.2 - top * 0.02],
                         ticksuffix="′", gridcolor="#EEF0F3", griddash="dash", zeroline=False, fixedrange=True)
    return base_layout(fig, height)


def speed_bars(subject, medians, name):
    """E6: grouped bars of km/h per stage type, subject in stage-type colour, median in grey."""
    types = [t for t in TYPE_COLOURS if t in medians]
    labels = [TYPE_LABELS[t] for t in types]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=[subject.get(t) for t in types], name=name,
        marker_color=[TYPE_COLOURS[t] for t in types],
        text=[f"{subject[t]:.1f}" if t in subject else "" for t in types], textposition="outside",
        hovertemplate="%{x}: %{y:.1f} km/h<extra>" + name.replace("<", "") + "</extra>",
    ))
    fig.add_trace(go.Bar(
        x=labels, y=[medians[t] for t in types], name="Peloton median", marker_color="#D5D8DE",
        text=[f"{medians[t]:.1f}" for t in types], textposition="outside",
        hovertemplate="%{x}: %{y:.1f} km/h<extra>Peloton median</extra>",
    ))
    top = max([medians[t] for t in types] + [v for v in subject.values() if v]) * 1.08
    fig.update_yaxes(title="km/h", range=[25, top], gridcolor="#EEF0F3", fixedrange=True)
    fig.update_xaxes(fixedrange=True)
    return base_layout(fig, 300, barmode="group")


def h_bars(labels, values, colours, texts=None, height=None, label_width=None):
    """Horizontal bars, largest on top."""
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h", marker_color=colours,
        text=texts if texts is not None else values, textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{text}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", fixedrange=True, type="category", tickmode="linear")
    fig.update_xaxes(visible=False, fixedrange=True, range=[0, max(values or [1]) * 1.16])
    base_layout(fig, height or 26 * len(labels) + 30)
    fig.update_layout(margin=dict(l=label_width or 8, r=12, t=4, b=4), yaxis_automargin=label_width is None)
    return fig


def v_bars(labels, values, colour, texts, height=170):
    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colour, text=texts, textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{text}<extra></extra>",
    ))
    fig.update_yaxes(visible=False, fixedrange=True)
    fig.update_xaxes(type="category", fixedrange=True)
    base_layout(fig, height)
    fig.update_layout(margin=dict(l=4, r=4, t=24, b=24))
    return fig


def choropleth(iso3, counts, names):
    fig = go.Figure(go.Choropleth(
        locations=iso3, z=counts, text=names, locationmode="ISO-3",
        colorscale=[[0, "#E4ECF7"], [1, "#2E5FA8"]], marker_line_color="#FFFFFF",
        colorbar=dict(title="Riders", thickness=10),
        hovertemplate="%{text}: %{z} riders<extra></extra>",
    ))
    fig.update_geos(showframe=False, showcoastlines=False, showcountries=True, countrycolor="#FFFFFF", showland=True, landcolor="#F0F1F4",
                    projection_type="natural earth", projection_rotation_lon=10, lataxis_range=[-50, 75], bgcolor="#FFFFFF")
    base_layout(fig, 320)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))
    return fig


def slope(rows, left_title, right_title, height=None):
    """E7: each rider's rank in two GCs, joined by a line. rows: name, colour, left, right, bold.
    The band marks the top 10; a rider crossing the dashed line enters or leaves it."""
    fig = go.Figure()
    worst = max(max(rows["left"]), max(rows["right"]))
    fig.add_hrect(y0=0.5, y1=10.5, fillcolor="#FBF6E0", line_width=0, layer="below")
    fig.add_hline(y=10.5, line=dict(color="#B58D00", width=1, dash="dash"))
    for r in rows.itertuples():
        moved = (r.left <= 10) != (r.right <= 10)
        arrow = "" if r.left == r.right else (" ▲" if r.right < r.left else " ▼")
        fig.add_trace(go.Scatter(
            x=[0, 1], y=[r.left, r.right], mode="lines+markers+text",
            line=dict(color=r.colour, width=4 if moved or r.bold else 2),
            marker=dict(size=9, color=r.colour),
            text=[f"{r.left}. {r.name}  ", f"  {r.right}. {r.name}{arrow}"], textposition=["middle left", "middle right"],
            textfont=dict(size=12, color="#15171C" if r.bold or moved else "#5B6170"),
            hovertext=f"{r.name}: {left_title} {r.left} → {right_title} {r.right}", hoverinfo="text",
        ))
    fig.update_xaxes(range=[-0.9, 1.9], tickvals=[0, 1], ticktext=[f"<b>{left_title}</b>", f"<b>{right_title}</b>"],
                     side="top", showgrid=False, zeroline=False, fixedrange=True)
    fig.update_yaxes(range=[worst + 0.7, 0.3], visible=False, fixedrange=True)
    base_layout(fig, height or 24 * worst + 70)
    fig.update_layout(margin=dict(l=8, r=8, t=36, b=8))
    return fig


def rank_dots(rows, height=None):
    """E4: one row per rider, a marker for each classification rank on a log axis (1 at the left).
    rows: label (HTML), gc, young, mountain (None when not ranked)."""
    fig = go.Figure()
    labels = list(rows["label"])
    for r in rows.itertuples():
        ranks = [v for v in (r.gc, r.young, r.mountain) if v is not None and v == v]
        if len(ranks) > 1:
            fig.add_trace(go.Scatter(x=[min(ranks), max(ranks)], y=[r.label, r.label], mode="lines",
                                     line=dict(color="#D5D8DE", width=6), hoverinfo="skip", showlegend=False))
    series = [("gc", "Overall GC", "circle", "#15171C", 12), ("young", "Young rider GC", "diamond-open", "#5B6170", 12),
              ("mountain", "Mountain GC proxy", "triangle-up", TYPE_COLOURS["mountain"], 13)]
    for column, name, symbol, colour, size in series:
        part = rows[rows[column].notna()]
        fig.add_trace(go.Scatter(
            x=part[column], y=part["label"], mode="markers", name=name,
            marker=dict(symbol=symbol, size=size, color=colour, line=dict(width=2, color=colour)),
            hovertemplate="%{y}<br>" + name + ": %{x}<extra></extra>",
        ))
    worst = max(rows[["gc", "young", "mountain"]].max(skipna=True).max(), 10)
    ticks = [t for t in RANK_TICKS if t <= worst * 1.2]
    fig.update_xaxes(type="log", range=[math.log10(0.8), math.log10(worst * 1.25)], tickvals=ticks, ticktext=[str(t) for t in ticks],
                     title="Rank (log scale, 1 = best)", gridcolor="#EEF0F3", griddash="dash", fixedrange=True)
    fig.update_yaxes(categoryorder="array", categoryarray=labels[::-1], fixedrange=True)
    base_layout(fig, height or 30 * len(rows) + 90)
    fig.update_layout(showlegend=True, legend=dict(orientation="h", y=1.02, yanchor="bottom", x=0), margin=dict(l=8, r=12, t=36, b=40),
                      yaxis_automargin=True)
    return fig


def team_gap_lines(rows, stages, ctx, height=380):
    """Best Team after each stage: gap to the leading team in minutes, leader on top.
    rows: fn_best_team_by_stage output. Other teams are thin grey lines behind my team and the rivals."""
    fig = go.Figure()
    _stage_axis(fig, stages)
    order = sorted(rows["team"].unique(), key=lambda t: (t == ctx.my, t in ctx.rivals))
    last_seq = rows["seq"].max()
    for team_name in order:
        part = rows[rows["team"] == team_name].sort_values("seq")
        focus = ctx.is_focus(team_name)
        fig.add_trace(go.Scatter(
            x=part["seq"], y=part["gap"] / 60, mode="lines", name=team_name,
            line=dict(color=ctx.colour(team_name), width=4 if team_name == ctx.my else 2.6 if focus else 1.2),
            opacity=1 if focus else 0.7,
            hovertext=[f"<b>{team_name}</b><br>Stage {n}: Best Team {r} · {fmt.gap(g) if g else 'leader'}"
                       for n, r, g in zip(part["stage_no"], part["team_rank"], part["gap"])], hoverinfo="text",
        ))
        end = part[part["seq"] == last_seq]
        if focus and not end.empty:
            fig.add_annotation(x=last_seq, y=end.iloc[0].gap / 60, text=f"{int(end.iloc[0].team_rank)}. {team_name}", showarrow=False,
                               xanchor="left", xshift=8, font=dict(size=12, color=ctx.colour(team_name)))
    # The axis fits my team and the rivals; teams further behind run off the bottom
    focus_rows = rows[rows["team"].map(ctx.is_focus)]
    top = max((focus_rows["gap"].max() if not focus_rows.empty else rows["gap"].max()) * 1.4, 300) / 60
    fig.update_xaxes(range=[0.5, len(stages) + 0.5 + max(4.0, len(stages) * 0.3)])
    fig.update_yaxes(title="Minutes behind the leading team", autorange=False, range=[top * 1.05, -top * 0.03],
                     ticksuffix="′", gridcolor="#EEF0F3", griddash="dash", zeroline=False, fixedrange=True)
    return base_layout(fig, height)


def heatmap(teams, columns, values, ctx, height=None):
    """E14: teams × stage types, each cell the number of top-10 finishes. values: one row per team."""
    labels = [f'<span style="color:{ctx.colour(t.split(" · ")[0]) if ctx.is_focus(t.split(" · ")[0]) else "#15171C"}">'
              f'{"<b>" + t + "</b>" if ctx.is_focus(t.split(" · ")[0]) else t}</span>' for t in teams]
    fig = go.Figure(go.Heatmap(
        z=values, x=columns, y=teams, colorscale=[[0, "#F7F8FA"], [0.001, "#E4ECF7"], [1, "#2E5FA8"]],
        texttemplate="%{z}", textfont=dict(size=12), xgap=3, ygap=3, showscale=False,
        hovertemplate="%{y}<br>%{x}: %{z} top-10 finishes<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", fixedrange=True, tickvals=teams, ticktext=labels)
    fig.update_xaxes(side="top", fixedrange=True)
    base_layout(fig, height or 24 * len(teams) + 60)
    fig.update_layout(margin=dict(l=8, r=8, t=30, b=8), yaxis_automargin=True)
    return fig
