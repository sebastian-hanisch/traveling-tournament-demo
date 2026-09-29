"""Kennzahlen: Distanzvergleich naiv/lokale Suche/CP-SAT, Sweep ueber n, CP-SAT-Skalierungsgrenze."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from ttp_scenario import Scenario, generate_scenario
from ttp_scheduler import U_MAX_DEFAULT, local_search, naive_schedule, solve_exact, total_distance

PRECOMPUTED_PATH = Path(__file__).resolve().parent / "precomputed_sweep.json"


@dataclass(frozen=True)
class MethodComparison:
    n_teams: int
    naive_distance: float
    local_search_distance: float
    cp_sat_distance: float | None
    cp_sat_is_proven: bool | None


def compare_methods(
    n_teams: int,
    seed: int,
    u_max: int = U_MAX_DEFAULT,
    ls_iters: int = 8000,
    ls_seed: int = 1,
    run_cp_sat: bool = False,
    cp_sat_time_limit_s: float = 20.0,
) -> MethodComparison:
    scenario = generate_scenario(n_teams, seed)
    start = naive_schedule(n_teams)
    naive_d = total_distance(start, scenario)
    _best, best_d = local_search(scenario, start, iters=ls_iters, seed=ls_seed, u_max=u_max)

    cp_sat_d = None
    cp_sat_proven = None
    if run_cp_sat:
        _sched, cp_sat_d, cp_sat_proven = solve_exact(scenario, u_max=u_max, time_limit_s=cp_sat_time_limit_s)

    return MethodComparison(
        n_teams=n_teams,
        naive_distance=naive_d,
        local_search_distance=best_d,
        cp_sat_distance=cp_sat_d,
        cp_sat_is_proven=cp_sat_proven,
    )


def sweep_methods(n_values: list[int], seed: int = 5, **kwargs) -> list[MethodComparison]:
    return [compare_methods(n, seed=seed, **kwargs) for n in n_values]


@dataclass(frozen=True)
class CpSatScalingPoint:
    n_teams: int
    seconds: float
    is_proven: bool
    distance: float | None  # None, wenn CP-SAT nicht einmal eine gueltige Loesung fand (siehe solve_exact)


def cp_sat_scaling(n_values: list[int], seed: int = 5, u_max: int = U_MAX_DEFAULT, time_limit_s: float = 30.0):
    points = []
    for n in n_values:
        scenario = generate_scenario(n, seed)
        t0 = time.perf_counter()
        _sched, dist, is_proven = solve_exact(scenario, u_max=u_max, time_limit_s=time_limit_s)
        dt = time.perf_counter() - t0
        points.append(CpSatScalingPoint(n_teams=n, seconds=dt, is_proven=is_proven, distance=dist))
    return points


def load_precomputed():
    """Liest die per `generate_precomputed.py` einmalig vorgerechneten Sweeps - die App darf diese NIE
    live nachrechnen (mehrere CP-SAT-Loesungen je bis zu 20s je Sweep-Punkt, siehe Skript-Docstring)."""
    with open(PRECOMPUTED_PATH, encoding="utf-8") as f:
        data = json.load(f)
    sweep = [MethodComparison(cp_sat_distance=None, cp_sat_is_proven=None, **row) for row in data["sweep"]]
    sweep_cp_sat = [MethodComparison(**row) for row in data["sweep_cp_sat"]]
    scaling = [CpSatScalingPoint(**row) for row in data["cp_sat_scaling"]]
    return sweep, sweep_cp_sat, scaling
