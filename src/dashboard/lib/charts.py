"""Plotly charts. Stage-type colours come from ui.TYPE_COLOURS so each type looks the same everywhere."""
import plotly.graph_objects as go

from lib import format as fmt
from lib.ui import TYPE_COLOURS, TYPE_LABELS

RIDER_LINES = ["#D4A200", "#2E5FA8", "#C0392B", "#17866A", "#7A5CC2", "#D9701E", "#2A9DB5", "#8C5A3C", "#5B6170", "#C2408E"]
MOUNTAIN_BAND = "#F6EBE6"
FONT = dict(family="Barlow, system-ui, sans-serif", size=13, color="#15171C")
RANK_FLOOR = 20


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


def gc_lines(gc, stages, bibs, measure="rank", inflections=None, yellow=None, pivots=None, focus=None, height=380):
    """GC storyline (E10) and GC standing (E1). measure: 'rank' or 'time' (gap to the leader).
    The inverted y axis puts the leader on top in both views."""
    fig = go.Figure()
    _stage_axis(fig, stages)
    seq_label = dict(zip(stages["seq"], stages["route"]))
    stage_of = dict(zip(stages["stage_no"], stages["seq"]))

    def y_value(row_rank, row_gap):
        return min(row_rank, RANK_FLOOR) if measure == "rank" else row_gap / 60

    positions = {}
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
        width = 4.5 if bib == focus else (3.2 if i == 0 and focus is None else 2.2)
        fig.add_trace(go.Scatter(
            x=rows["seq"], y=ys, mode="lines", name=rows["rider_name"].iloc[0],
            line=dict(color=RIDER_LINES[i % len(RIDER_LINES)], width=width),
            hovertext=hover, hoverinfo="text",
        ))

    if inflections is not None and not inflections.empty:
        for takes, size in ((False, 9), (True, 15)):
            part = inflections[inflections["takes_yellow"] == takes]
            xs, ys, text, colours = [], [], [], []
            for row in part.itertuples():
                if row.rider_bib in positions and row.stage_no in positions[row.rider_bib]:
                    xs.append(stage_of[row.stage_no])
                    ys.append(positions[row.rider_bib][row.stage_no])
                    text.append(f"{row.rider_name} · Stage {row.stage_no}: GC {row.prev_rank} → {row.gc_rank}")
                    colours.append(RIDER_LINES[bibs.index(row.rider_bib) % len(RIDER_LINES)])
            if xs:
                fig.add_trace(go.Scatter(
                    x=xs, y=ys, mode="markers", hovertext=text, hoverinfo="text",
                    marker=dict(size=size, color="#F5C400" if takes else "#FFFFFF",
                                line=dict(width=2, color="#15171C" if takes else colours)),
                ))

    if pivots is not None and not pivots.empty:
        for row in pivots.itertuples():
            if row.rider_bib in positions and row.stage_no in positions[row.rider_bib]:
                fig.add_trace(go.Scatter(
                    x=[stage_of[row.stage_no]], y=[positions[row.rider_bib][row.stage_no]], mode="markers",
                    hovertext=[f"Pivotal stage {row.stage_no}"], hoverinfo="text",
                    marker=dict(symbol="diamond", size=13, color="#15171C",
                                line=dict(width=2, color=RIDER_LINES[bibs.index(row.rider_bib) % len(RIDER_LINES)])),
                ))

    if yellow is not None:
        for row in yellow[yellow["is_change"]].itertuples():
            fig.add_annotation(
                x=row.seq, y=1.02, yref="paper", yanchor="bottom", showarrow=False, text=f"<b>{row.change_no}</b>",
                bgcolor="#F5C400", font=dict(color="#15171C", size=12), borderpad=3,
                hovertext=f"Stage {row.stage_no}: {row.holder_name} takes yellow",
            )

    if measure == "rank":
        fig.update_yaxes(title="GC position", autorange=False, range=[RANK_FLOOR + 0.5, 0.5],
                         tickvals=[1, 5, 10, 15, 20], ticktext=["1", "5", "10", "15", "20+"],
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
