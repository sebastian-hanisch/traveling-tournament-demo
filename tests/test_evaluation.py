"""Verfahrensvergleich und CP-SAT-Skalierungsgrenze - die zentrale Behauptung dieses Stuecks."""

import pytest

from ttp_evaluation import compare_methods, cp_sat_scaling, sweep_methods


@pytest.mark.parametrize("n", [4, 6, 8])
def test_local_search_beats_or_matches_naive(n):
    cmp = compare_methods(n, seed=5, ls_iters=3000)
    assert cmp.local_search_distance <= cmp.naive_distance


def test_compare_methods_with_cp_sat_at_small_n():
    cmp = compare_methods(4, seed=5, run_cp_sat=True, cp_sat_time_limit_s=10.0, ls_iters=3000)
    assert cmp.cp_sat_is_proven
    assert cmp.local_search_distance >= cmp.cp_sat_distance - 1e-6


def test_sweep_methods_returns_one_entry_per_n():
    results = sweep_methods([4, 6, 8], seed=5, ls_iters=2000)
    assert [c.n_teams for c in results] == [4, 6, 8]


def test_cp_sat_proves_optimal_at_n4_but_not_reliably_beyond():
    """Kernbefund dieses Stuecks: CP-SAT beweist bei n=4 das Optimum sofort, aber nicht mehr bei n=10
    innerhalb eines kurzen Zeitlimits - anders als Stueck 4, wo CP-SAT bis n=50 durchgehend bewiesen
    optimal war. n=10 statt eines knappen n=8 gewaehlt, um Zufallstreffer auf schnellerer CI-Hardware
    unwahrscheinlich zu machen (siehe project memory zu CI-robusten Zahlen-Asserts)."""
    points = cp_sat_scaling([4, 10], time_limit_s=5.0)
    assert points[0].is_proven
    assert not points[1].is_proven
