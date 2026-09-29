"""Plotly-Visualisierungen: Reiseroute eines Team im Fokus auf der Karte (wachsendes Beispiel),
Verfahrens-Vergleichsdiagramm, CP-SAT-Skalierungsgrenze. Alle Figuren per lock_axes gesperrt
(Touch-Scrolling-Konvention des Portfolios)."""

from __future__ import annotations

import plotly.graph_objects as go

from ttp_evaluation import CpSatScalingPoint, MethodComparison
from ttp_scenario import Scenario
from ttp_scheduler import Schedule

HOME_COLOR = "#1f77b4"
CITY_COLOR = "#8a8f98"
ROUTE_COLOR = "#d68a2e"
NAIVE_COLOR = "#c0392b"
LS_COLOR = "#2ca02c"
CPSAT_COLOR = "#1f77b4"


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _team_trip(schedule: Schedule, team: int, upto_round: int) -> list[int]:
    """Stationen von Team `team` von der eigenen Stadt bis nach Runde `upto_round` (1-indiziert)."""
    stations = [team]
    for rnd in schedule.rounds[:upto_round]:
        m = next(mm for mm in rnd.matches if mm.home == team or mm.away == team)
        stations.append(team if m.home == team else m.home)
    return stations


def build_route_map(scenario: Scenario, schedule: Schedule, focus_team: int, upto_round: int) -> go.Figure:
    xs = [c[0] for c in scenario.cities]
    ys = [c[1] for c in scenario.cities]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=xs, y=ys, mode="markers+text",
            text=[str(t) for t in range(scenario.n_teams)],
            textposition="top center",
            marker=dict(size=14, color=CITY_COLOR),
            name="Heimatstädte", hoverinfo="text",
        )
    )

    stations = _team_trip(schedule, focus_team, upto_round)
    route_x = [scenario.cities[s][0] for s in stations]
    route_y = [scenario.cities[s][1] for s in stations]
    fig.add_trace(
        go.Scatter(
            x=route_x, y=route_y, mode="lines+markers",
            line=dict(color=ROUTE_COLOR, width=3),
            marker=dict(size=10, color=ROUTE_COLOR),
            name=f"Route Team {focus_team}",
        )
    )
    hx, hy = scenario.cities[focus_team]
    fig.add_trace(
        go.Scatter(
            x=[hx], y=[hy], mode="markers",
            marker=dict(size=20, color=HOME_COLOR, symbol="star", line=dict(width=1.5, color="white")),
            name=f"Heimat Team {focus_team}",
        )
    )

    fig.update_xaxes(range=[-5, 105], title="")
    fig.update_yaxes(range=[-5, 105], title="", scaleanchor="x", scaleratio=1)
    fig.update_layout(
        template="plotly_white", height=460, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", y=-0.1),
    )
    return lock_axes(fig)


def build_comparison_chart(comparisons: list[MethodComparison]) -> go.Figure:
    ns = [c.n_teams for c in comparisons]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ns, y=[c.naive_distance for c in comparisons], mode="lines+markers",
                              line=dict(color=NAIVE_COLOR, width=3), name="naiv (Stück 4)"))
    fig.add_trace(go.Scatter(x=ns, y=[c.local_search_distance for c in comparisons], mode="lines+markers",
                              line=dict(color=LS_COLOR, width=3), name="Lokale Suche"))
    cpsat_ns = [c.n_teams for c in comparisons if c.cp_sat_distance is not None]
    cpsat_ds = [c.cp_sat_distance for c in comparisons if c.cp_sat_distance is not None]
    if cpsat_ns:
        fig.add_trace(go.Scatter(x=cpsat_ns, y=cpsat_ds, mode="lines+markers",
                                  line=dict(color=CPSAT_COLOR, width=3, dash="dot"), name="CP-SAT"))
    fig.update_xaxes(title="Teamzahl", fixedrange=True, dtick=2)
    fig.update_yaxes(title="Gesamt-Reisedistanz", fixedrange=True, rangemode="tozero")
    fig.update_layout(template="plotly_white", height=380, margin=dict(l=10, r=10, t=20, b=10),
                       legend=dict(orientation="h", y=-0.22))
    return fig


def build_cp_sat_scaling_chart(points: list[CpSatScalingPoint]) -> go.Figure:
    ns = [p.n_teams for p in points]
    secs = [p.seconds for p in points]
    colors = [CPSAT_COLOR if p.is_proven else NAIVE_COLOR for p in points]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ns, y=secs, mode="lines", line=dict(color="#8a8f98", width=2)))
    fig.add_trace(
        go.Scatter(
            x=ns, y=secs, mode="markers",
            marker=dict(size=12, color=colors, line=dict(width=1.5, color="white")),
            text=["bewiesen optimal" if p.is_proven else "NICHT bewiesen (Zeitlimit)" for p in points],
            hoverinfo="text",
            showlegend=False,
        )
    )
    fig.update_xaxes(title="Teamzahl", fixedrange=True, dtick=2)
    fig.update_yaxes(title="CP-SAT-Laufzeit (Sekunden)", fixedrange=True, rangemode="tozero")
    fig.update_layout(template="plotly_white", height=320, margin=dict(l=10, r=10, t=20, b=10))
    return fig
