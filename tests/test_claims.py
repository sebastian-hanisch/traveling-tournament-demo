"""Regressionstests gegen die konkreten Zahlen aus README.md."""

import pytest

from ttp_evaluation import compare_methods, cp_sat_scaling


@pytest.mark.parametrize(
    "n, naive, local_search",
    [
        (8, 5609.7, 3946.9),
        (12, 14753.9, 10145.7),
    ],
)
def test_readme_distance_numbers(n, naive, local_search):
    # deterministisch (reines Python, fester RNG-Seed, kein CP-SAT beteiligt) - enge absolute Toleranz
    # statt einer prozentualen, siehe project memory zu CI-robusten Zahlen-Asserts
    cmp = compare_methods(n, seed=5, ls_iters=8000, ls_seed=1)
    assert cmp.naive_distance == pytest.approx(naive, abs=0.5)
    assert cmp.local_search_distance == pytest.approx(local_search, abs=0.5)


def test_readme_n4_cp_sat_proven_instantly():
    cmp = compare_methods(4, seed=5, run_cp_sat=True, cp_sat_time_limit_s=10.0, ls_iters=8000)
    assert cmp.cp_sat_is_proven


def test_readme_local_search_beats_cp_sat_bound_at_n14():
    """Kernbefund: bei 14 Teams findet die lokale Suche eine BESSERE Loesung als CP-SAT im gleichen
    Zeitbudget (20s) liefert. n=14 statt eines knapperen n=12 gewaehlt: bei n=12 lag CP-SATs
    (nicht-deterministische, zeitlimitierte) obere Schranke in wiederholten Messungen mal knapp
    ueber, mal knapp unter dem lokalen-Suche-Ergebnis (10.406-10.811 vs. deterministisch 10.439 mit der frueheren, nicht break-minimalen naiven Startloesung; heute 10.146) -
    bei n=14 war die lokale Suche in 3/3 Wiederholungen klar und mit Sicherheitsabstand besser
    (15.933-16.420 vs. deterministisch 14.625, mindestens ~8% Abstand) - robuster gegen CI-Varianz."""
    cmp = compare_methods(14, seed=5, run_cp_sat=True, cp_sat_time_limit_s=20.0, ls_iters=8000)
    assert not cmp.cp_sat_is_proven
    assert cmp.local_search_distance < cmp.cp_sat_distance * 0.98


def test_readme_cp_sat_scaling_n4_proven_n10_not():
    points = cp_sat_scaling([4, 10], time_limit_s=5.0)
    assert points[0].is_proven
    assert not points[1].is_proven
