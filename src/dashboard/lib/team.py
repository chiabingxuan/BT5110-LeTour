"""The team manager's point of view: My team and its Rivals, chosen in the sidebar on every page.

Every chart colours a team by its role: my team in a bold accent, rivals in muted teals, the rest grey.
Stage-type colours (ui.TYPE_COLOURS) are separate and unchanged.
"""
from dataclasses import dataclass
from html import escape

import streamlit as st

from lib import queries

MY = "#C2185B"
RIVALS = ["#1F6F78", "#4FA3A5", "#86C5C2", "#2F8F83", "#5E9EA0"]
OTHER = "#C9CDD4"
DEFAULT_TEAM = "UAE TEAM EMIRATES XRG"


@dataclass(frozen=True)
class Context:
    my: str
    rivals: tuple

    def colour(self, team):
        if team == self.my:
            return MY
        if team in self.rivals:
            return RIVALS[self.rivals.index(team) % len(RIVALS)]
        return OTHER

    def is_focus(self, team):
        """My team or a rival: the teams a chart labels by name."""
        return team == self.my or team in self.rivals

    def label(self, team):
        """Team name as HTML, coloured by its role."""
        colour = self.colour(team) if self.is_focus(team) else "#5B6170"
        weight = 700 if team == self.my else 600 if team in self.rivals else 400
        return f'<span style="color:{colour};font-weight:{weight}">{escape(team)}</span>'


def default_rivals(my, n=3):
    """The n best teams in the race-wide Best Team classification other than my team."""
    return [t for t in queries.best_team_order() if t != my][:n]


def _reset_rivals():
    st.session_state.w_rivals = default_rivals(st.session_state.w_my_team)


def _ensure(teams):
    """Sets the defaults and drops stale choices. Pages call it too, as tests may run a page without app.py."""
    state = st.session_state
    if state.get("w_my_team") not in teams:
        state.w_my_team = DEFAULT_TEAM if DEFAULT_TEAM in teams else teams[0]
    if "w_rivals" not in state:
        state.w_rivals = default_rivals(state.w_my_team)
    state.w_rivals = [t for t in state.w_rivals if t in teams and t != state.w_my_team]


def sidebar():
    """Draws the My team and Rivals pickers. app.py calls it on every page, so they read like a global setting."""
    state = st.session_state
    teams = queries.team_names()["name"].tolist()
    _ensure(teams)
    st.selectbox("My team", teams, key="w_my_team", on_change=_reset_rivals)
    st.multiselect("Rivals", [t for t in teams if t != state.w_my_team], key="w_rivals", max_selections=5,
                   placeholder="No rivals", help="Default: the three best other teams in the Best Team classification.")


def context():
    state = st.session_state
    if "w_my_team" not in state or "w_rivals" not in state:
        _ensure(queries.team_names()["name"].tolist())
    return Context(state.w_my_team, tuple(state.w_rivals))


def swatches(ctx):
    """A one-line colour key for my team and the rivals."""
    items = [(ctx.my, MY)] + [(t, ctx.colour(t)) for t in ctx.rivals] + [("Other teams", OTHER)]
    return "".join(
        f'<span style="display:inline-flex;align-items:center;gap:6px;margin-right:14px;font-size:13px">'
        f'<i style="width:12px;height:12px;border-radius:3px;background:{c};display:inline-block"></i>{escape(t)}</span>'
        for t, c in items
    )
