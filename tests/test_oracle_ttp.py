"""Unabhaengige Orakel fuer das TTP: Brute-Force-Enumeration aller gueltigen 4-Team-Spielplaene
(eigener Gueltigkeitstest ueber Gegnermatrix, eigene Distanzrechnung ueber Standortfolgen) und
Literaturwerte der Benchmarks CIRC4 (20) und NL4 (8276) aus Easton, Nemhauser & Trick (2001)."""

import itertools
import random

import numpy as np

from ttp_scenario import Scenario, generate_scenario
from ttp_scheduler import Match, Round, Schedule, is_valid, solve_exact, total_distance


def _enumerate_valid_n4(u):
    matchings = [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]
    options = []
    for mt in matchings:
        for flips in itertools.product((0, 1), repeat=2):
            options.append(tuple((a, b) if f == 0 else (b, a) for (a, b), f in zip(mt, flips)))
    found = []

    def rec(rounds, used):
        if len(rounds) == 6:
            found.append(tuple(rounds))
            return
        for op in options:
            if any(m in used for m in op):
                continue
            if rounds and {frozenset(m) for m in op} & {frozenset(m) for m in rounds[-1]}:
                continue
            cand = rounds + [op]
            ok = True
            for t in range(4):
                run = 1
                seq = [any(m[0] == t for m in rd) for rd in cand]
                for k in range(1, len(seq)):
                    run = run + 1 if seq[k] == seq[k - 1] else 1
                    if run > u:
                        ok = False
            if ok:
                rec(cand, used | set(op))

    rec([], frozenset())
    return found


def _arc_counts(rounds):
    arcs = np.zeros((4, 4))
    for t in range(4):
        loc = t
        for rd in rounds:
            venue = next(a for a, b in rd if t in (a, b))  # Spielort = Heimteam
            arcs[loc, venue] += 1
            loc = venue
        arcs[loc, t] += 1
    return arcs


def _to_schedule(rounds):
    return Schedule(4, tuple(Round(tuple(Match(a, b) for a, b in rd)) for rd in rounds))


def test_brute_force_optimum_n4_matches_solve_exact():
    schedules = _enumerate_valid_n4(3)
    assert len(schedules) == 1920
    arcs = np.array([_arc_counts(s) for s in schedules])
    for seed in range(6):
        scen = generate_scenario(4, seed)
        optimum = (arcs * np.array(scen.distances)).sum(axis=(1, 2)).min()
        sched, dist, proven = solve_exact(scen, time_limit_s=10.0)
        assert proven
        assert abs(dist - optimum) < 0.01
        assert is_valid(sched)[0]
        assert abs(total_distance(sched, scen) - optimum) < 0.01


def test_is_valid_agrees_with_enumeration_on_random_structures():
    valid = set(_enumerate_valid_n4(3))
    rng = random.Random(3)
    options = list(itertools.chain.from_iterable(
        [tuple((a, b) if f == 0 else (b, a) for (a, b), f in zip(mt, flips))
         for flips in itertools.product((0, 1), repeat=2)]
        for mt in [((0, 1), (2, 3)), ((0, 2), (1, 3)), ((0, 3), (1, 2))]
    ))
    for _ in range(3000):
        rounds = tuple(rng.choice(options) for _ in range(6))
        assert is_valid(_to_schedule(rounds))[0] == (rounds in valid)


def test_u_max_variants_n4_against_enumeration():
    assert len(_enumerate_valid_n4(1)) == 0  # U=1 unmoeglich
    scen = generate_scenario(4, 11)
    sched, dist, _proven = solve_exact(scen, u_max=1, time_limit_s=10.0)
    assert sched is None and dist is None
    arcs = np.array([_arc_counts(s) for s in _enumerate_valid_n4(2)])
    optimum = (arcs * np.array(scen.distances)).sum(axis=(1, 2)).min()
    _s, dist2, proven2 = solve_exact(scen, u_max=2, time_limit_s=10.0)
    assert proven2 and abs(dist2 - optimum) < 0.01


def test_literature_benchmarks_circ4_nl4():
    zero = tuple((0.0, 0.0) for _ in range(4))
    circ4 = Scenario(4, 0, zero, tuple(tuple(float(min(abs(i - j), 4 - abs(i - j))) for j in range(4)) for i in range(4)))
    nl4_matrix = ((0, 745, 665, 929), (745, 0, 80, 337), (665, 80, 0, 380), (929, 337, 380, 0))
    nl4 = Scenario(4, 0, zero, tuple(tuple(float(x) for x in row) for row in nl4_matrix))
    for scen, literature in ((circ4, 20.0), (nl4, 8276.0)):
        sched, dist, proven = solve_exact(scen, time_limit_s=10.0)
        assert proven and abs(dist - literature) < 1e-6
        assert abs(total_distance(sched, scen) - literature) < 1e-6


# --- naive_schedule: Break-Minimum (Orakel: Brute Force bei kleinem n, Untergrenze 3n-6 für den
# gespiegelten Doppelrundenplan) und Determinismus ---


def _breaks(schedule):
    """Eigene Break-Zählung: aufeinanderfolgende Runden mit gleichem Heim/Auswärts-Status je Team."""
    total = 0
    for t in range(schedule.n_teams):
        status = [any(m.home == t for m in rd.matches) for rd in schedule.rounds]
        total += sum(status[k] == status[k - 1] for k in range(1, len(status)))
    return total


def _brute_force_min_breaks(n):
    """Kleinste Break-Zahl über ALLE Heim/Auswärts-Zuordnungen der Zirkelmethode-Paarstruktur
    (jedes Paar: wer im ersten Spiel Heimrecht hat; das Rückspiel kehrt es um)."""
    from ttp_scheduler import _pair_rounds

    rounds = _pair_rounds(n)
    leg = len(rounds) // 2
    pairs = [p for rd in rounds[:leg] for p in rd]
    best = None
    for bits in range(2 ** len(pairs)):
        k = 0
        per_round = []
        for rd in rounds[:leg]:
            st = {}
            for a, b in rd:
                st[a] = (bits >> k) & 1
                st[b] = 1 - st[a]
                k += 1
            per_round.append(st)
        seq = {t: [per_round[r][t] for r in range(leg)] + [1 - per_round[r][t] for r in range(leg)] for t in range(n)}
        total = sum(sum(s[i] == s[i - 1] for i in range(1, len(s))) for s in seq.values())
        longest_ok = all(
            all(len(set(s[i:i + 4])) == 2 for i in range(len(s) - 3)) for s in seq.values()
        )
        if longest_ok and (best is None or total < best):
            best = total
    return best


def test_naive_schedule_break_minimum_by_brute_force():
    from ttp_scheduler import naive_schedule

    for n in (4, 6):
        sched = naive_schedule(n)
        assert is_valid(sched)[0]
        assert _brute_force_min_breaks(n) == 3 * n - 6
        assert _breaks(sched) == 3 * n - 6


def test_naive_schedule_reaches_break_lower_bound_3n_minus_6():
    # Untergrenze: höchstens 2 Teams ohne Break im ersten Abschnitt, jedes andere kostet mit
    # Spiegelung mindestens 3 -> 3(n-2); n=16 ist der Regler-Maximalwert der Demo.
    from ttp_scheduler import naive_schedule

    for n in range(4, 17, 2):
        sched = naive_schedule(n)
        assert is_valid(sched)[0]
        assert _breaks(sched) == 3 * n - 6


def test_naive_schedule_is_deterministic_at_n16():
    from ttp_scheduler import naive_schedule

    first = naive_schedule(16)
    assert naive_schedule(16, time_limit_s=1.0) == first
