"""The global filter bar shown on every data page. Widget values live in st.session_state (keys w_*)."""
from dataclasses import dataclass

import streamlit as st

from lib import format as fmt
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


def _summary(state, nation_names, rider_filters):
    """One line naming the active filters, shown as the title of the collapsed bar."""
    chosen = [t for t in (state.w_types or []) if t != "All"]
    parts = ["all 21 stages" if state.w_from == 1 and state.w_to == 21 else f"stages {state.w_from}–{state.w_to}"]
    if chosen:
        parts.append(" + ".join(chosen))
    if rider_filters and state.w_team:
        parts.append(state.w_team)
    if rider_filters and state.w_nation:
        parts.append(nation_names[state.w_nation])
    return ", ".join(parts)


def bar(rider_filters=False, young=False):
    """Draws the filter bar and returns the current Filters. Stops the page if no stage matches.

    The stage filters act on every page. rider_filters and young add the Team, Rider nation and
    Young rider controls on the pages they act on, so no control on screen is ever without effect.
    """
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

    active = (state.w_from != 1 or state.w_to != 21 or state.w_types != ["All"]
              or (rider_filters and (state.w_team or state.w_nation)) or (young and state.w_cutoff != 26))
    with st.container(key="card_filters"):
        with st.expander(f"Filters: {_summary(state, nation_names, rider_filters)}", expanded=bool(active)):
            widths = [1.45, 1.45, 3.0] + ([1.4, 1.4] if rider_filters else []) + ([1.3] if young else [])
            columns = iter(st.columns(widths, vertical_alignment="bottom"))
            next(columns).selectbox("Stages from", list(labels), key="w_from", format_func=labels.get, on_change=_keep_order, args=("from",))
            next(columns).selectbox("to", list(labels), key="w_to", format_func=labels.get, on_change=_keep_order, args=("to",))
            next(columns).pills("Stage type", ["All", *TYPE_VALUES], selection_mode="multi", key="w_types", on_change=_types_changed)
            if rider_filters:
                next(columns).selectbox("Team", teams, key="w_team", index=None, placeholder="All teams")
                next(columns).selectbox("Rider nation", list(nation_names), key="w_nation", index=None, placeholder="All nations",
                                        format_func=lambda iso: f"{nation_names[iso]} ({iso})")
            if young:
                next(columns).number_input(f"Young: age on {fmt.medium_date(start)} under", min_value=18, max_value=45, step=1, key="w_cutoff")
            chosen = [t for t in (state.w_types or []) if t != "All"]
            f = Filters(
                stage_from=int(state.w_from),
                stage_to=int(state.w_to),
                types=[TYPE_VALUES[t] for t in chosen] or None,
                team=state.w_team if rider_filters else None,
                nation=state.w_nation if rider_filters else None,
                cutoff=int(state.w_cutoff),
            )
            selected = queries.selected_stages(f)
            if not selected.empty:
                extra = " The team and nation filters narrow rider lists while ranks stay race-wide." if rider_filters else ""
                ui.note(f"{len(selected)} of 21 stages selected ({', '.join(map(str, selected['stage_no']))}). GC is recomputed over them.{extra}")
    if selected.empty:
        ui.html('<div class="callout">No stage matches these filters. Widen the stage range or pick another stage type.</div>')
        st.stop()
    return f
