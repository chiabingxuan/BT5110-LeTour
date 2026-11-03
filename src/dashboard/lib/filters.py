"""The global filter bar shown on every data page. Widget values live in st.session_state (keys w_*)."""
from dataclasses import dataclass

import streamlit as st

from lib import queries, ui

TYPE_VALUES = {"Flat": "flat", "Hilly": "hilly", "Mountain": "mountain", "ITT": "individual time-trial"}


@dataclass(frozen=True)
class Filters:
    stage_from: int
    stage_to: int
    types: list | None  # None means every stage type
    team: str | None
    nation: str | None
    cutoff: int

    def narrow(self, df, team_col="team", nation_col="rider_country"):
        """Applies the Team and Rider nation filters to a rider list. Ranks stay race-wide."""
        if self.team and team_col in df:
            df = df[df[team_col] == self.team]
        if self.nation and nation_col in df:
            df = df[df[nation_col] == self.nation]
        return df


def _keep_order(changed):
    """Keeps from <= to whichever of the two dropdowns moved."""
    state = st.session_state
    if state.w_from > state.w_to:
        if changed == "from":
            state.w_to = state.w_from
        else:
            state.w_from = state.w_to


def _types_changed():
    """All is exclusive: picking it clears the others, and picking another type clears All."""
    state = st.session_state
    current = state.w_types or []
    previous = state.get("_types_prev", ["All"])
    if "All" in current and "All" not in previous:
        state.w_types = ["All"]
    elif not [t for t in current if t != "All"]:
        state.w_types = ["All"]
    else:
        state.w_types = [t for t in current if t != "All"]
    state._types_prev = state.w_types


def bar():
    """Draws the filter bar and returns the current Filters. Stops the page if no stage matches."""
    state = st.session_state
    state.setdefault("w_from", 1)
    state.setdefault("w_to", 21)
    state.setdefault("w_types", ["All"])
    state.setdefault("w_team", None)
    state.setdefault("w_nation", None)
    state.setdefault("w_cutoff", 26)

    all_stages = queries.stages()
    start = all_stages["date"].min()
    labels = dict(zip(all_stages["stage_no"], "Stage " + all_stages["stage_no"].astype(str) + " · " + all_stages["type_label"]))
    teams = queries.team_names()["name"].tolist()
    nations = queries.rider_nations()
    nation_names = dict(zip(nations["iso"], nations["country_name"]))

    with st.container(border=True, key="card_filters"):
        c = st.columns([1.45, 1.45, 3.0, 1.4, 1.4, 1.3], vertical_alignment="bottom")
        c[0].selectbox("Stages from", list(labels), key="w_from", format_func=labels.get, on_change=_keep_order, args=("from",))
        c[1].selectbox("to", list(labels), key="w_to", format_func=labels.get, on_change=_keep_order, args=("to",))
        c[2].pills("Stage type", ["All", *TYPE_VALUES], selection_mode="multi", key="w_types", on_change=_types_changed)
        c[3].selectbox("Team", teams, key="w_team", index=None, placeholder="All teams")
        c[4].selectbox("Rider nation", list(nation_names), key="w_nation", index=None, placeholder="All nations",
                       format_func=lambda iso: f"{nation_names[iso]} ({iso})")
        c[5].number_input(f"Young: age on {start.strftime('%-d %b %Y')} under", min_value=18, max_value=45, step=1, key="w_cutoff")

        chosen = [t for t in (state.w_types or []) if t != "All"]
        f = Filters(
            stage_from=int(state.w_from),
            stage_to=int(state.w_to),
            types=[TYPE_VALUES[t] for t in chosen] or None,
            team=state.w_team,
            nation=state.w_nation,
            cutoff=int(state.w_cutoff),
        )
        selected = queries.selected_stages(f)
        if selected.empty:
            ui.note("No stage matches these filters. Widen the stage range or pick another stage type.")
        else:
            parts = [f"{len(selected)} of 21 stages ({', '.join(map(str, selected['stage_no']))})"]
            if f.team:
                parts.append(f"team: {f.team}")
            if f.nation:
                parts.append(f"nation: {nation_names[f.nation]}")
            ui.note("Showing " + " · ".join(parts) + ". GC is recomputed over the selected stages; "
                    "the team and nation filters narrow rider lists while ranks stay race-wide.")
    if selected.empty:
        st.stop()
    return f
