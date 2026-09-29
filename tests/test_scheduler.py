"""Strukturelle Korrektheit: naiver Spielplan, lokale Suche, CP-SAT - fuer alle drei muss die
TTP-Grundregel gelten (kein Wiederholungsspiel, hoechstens 3 gleiche Runden in Folge, jedes Paar genau
einmal je Seite zuhause)."""

import pytest

from ttp_scenario import generate_scenario
from ttp_scheduler import (
    is_valid,
    local_search,
    naive_schedule,
    round_count,
    solve_exact,
    total_distance,
)


@pytest.mark.parametrize("n", [4, 6, 8, 10])
def test_naive_schedule_is_valid(n):
    sched = naive_schedule(n)
    ok, reason = is_valid(sched)
    assert ok, reason
    assert len(sched.rounds) == round_count(n) == 2 * (n - 1)


@pytest.mark.parametrize("n", [4, 6, 8, 10])
def test_local_search_result_is_valid(n):
    scenario = generate_scenario(n, seed=5)
    start = naive_schedule(n)
    best, best_cost = local_search(scenario, start, iters=3000, seed=1)
    ok, reason = is_valid(best)
    assert ok, reason
    assert abs(total_distance(best, scenario) - best_cost) < 1e-6


@pytest.mark.parametrize("n", [4, 6, 8])
def test_local_search_never_worse_than_naive(n):
    scenario = generate_scenario(n, seed=5)
    start = naive_schedule(n)
    naive_d = total_distance(start, scenario)
    _best, best_cost = local_search(scenario, start, iters=3000, seed=1)
    assert best_cost <= naive_d


@pytest.mark.parametrize("n", [4, 6])
def test_cp_sat_result_is_valid(n):
    scenario = generate_scenario(n, seed=5)
    sched, dist, _is_proven = solve_exact(scenario, time_limit_s=10.0)
    ok, reason = is_valid(sched)
    assert ok, reason
    # CP-SAT rundet Distanzen auf ganze Promille (scale=1000) - Toleranz muss diese Diskretisierung
    # abdecken, nicht nur Gleitkomma-Rauschen.
    assert abs(total_distance(sched, scenario) - dist) < 0.01


def test_cp_sat_matches_local_search_at_n4_proven_optimal():
    """n=4 ist klein genug, dass CP-SAT innerhalb von 10s beweist optimal zu sein - Kreuz-Check, dass
    die lokale Suche dort dasselbe (oder ein schlechteres) Ergebnis findet, nie ein besseres."""
    scenario = generate_scenario(4, seed=5)
    sched, cp_sat_dist, is_proven = solve_exact(scenario, time_limit_s=10.0)
    assert is_proven
    start = naive_schedule(4)
    _best, ls_cost = local_search(scenario, start, iters=5000, seed=1)
    assert ls_cost >= cp_sat_dist - 1e-6


@pytest.mark.parametrize("n", [3, 5, 7])
def test_odd_n_rejected(n):
    with pytest.raises(ValueError):
        naive_schedule(n)


def test_is_valid_detects_repeat_violation():
    sched = naive_schedule(6)
    rounds = list(sched.rounds)
    rounds[1] = rounds[0]
    from ttp_scheduler import Schedule

    broken = Schedule(n_teams=6, rounds=tuple(rounds))
    ok, reason = is_valid(broken)
    assert not ok
