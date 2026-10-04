"""Traveling Tournament Problem (Easton, Nemhauser & Trick 2001): anders als Stück 4 ist hier der
GANZE Spielplan frei - nicht nur Heim/Auswärts fuer eine feste Paarstruktur, sondern welches Team wann
gegen wen antritt, gemeinsam mit Heim/Auswärts, um die Gesamt-Reisedistanz zu minimieren.

Drei Verfahren:
- `naive_schedule`: Stück 4s break-optimaler Spielplan (Zirkelmethode-Paarstruktur, CP-SAT-optimales
  Heim/Auswärts fuer Break-Minimierung) - ignoriert Geografie komplett, dient hier als Startpunkt UND
  als "naive" Vergleichspolitik.
- `local_search`: Standardzuege der TTP-Literatur (Anagnostopoulos, Michel, Van Hentenryck & Vergados
  2003) - SwapHomes, SwapRounds, SwapTeams - mit Simulated-Annealing-Akzeptanz, startet von
  `naive_schedule`. Bewusste Einschraenkung (siehe README "Wo die Annahmen enden"): alle drei Zuege
  aendern nie die ABSTRAKTE Zirkelmethode-Paarstruktur (nur Zuordnung, Reihenfolge, Heimrecht) - die
  allgemeine TTP erlaubt zusaetzlich GRUNDSAETZLICH andere Paarstrukturen.
- `solve_exact`: CP-SAT ueber ALLE moeglichen Paarstrukturen (x[i,j,r]-Modell), nur fuer kleine n
  praktikabel - bei groesserem n meist nicht mehr bewiesen optimal innerhalb des Zeitlimits (das IST
  der Kernbefund dieses Stuecks, siehe README).
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass

from ortools.sat.python import cp_model

from ttp_scenario import Scenario

U_MAX_DEFAULT = 3  # Standard-TTP (Easton/Nemhauser/Trick 2001): max. 3 gleiche Spiele in Folge
NUM_SEARCH_WORKERS = min(8, os.cpu_count() or 1)  # NIE hart auf eine Zahl setzen - siehe project memory


@dataclass(frozen=True)
class Match:
    home: int
    away: int


@dataclass(frozen=True)
class Round:
    matches: tuple[Match, ...]


@dataclass(frozen=True)
class Schedule:
    n_teams: int
    rounds: tuple[Round, ...]


# --- Zirkelmethode-Paarstruktur (identisch zu drr_scheduler.py, hier ohne Heim/Auswaertszuweisung) ---


def _single_leg_pairs(n_teams: int) -> list[list[tuple[int, int]]]:
    if n_teams < 4 or n_teams % 2 != 0:
        raise ValueError("n_teams muss gerade und mindestens 4 sein")
    fixed = n_teams - 1
    m = n_teams - 1
    step = (m + 1) // 2
    rounds: list[list[tuple[int, int]]] = []
    r_pos = 0
    for _round_index in range(m):
        pairs = [(r_pos, fixed)]
        for i in range(1, (m - 1) // 2 + 1):
            a = (r_pos - i) % m
            b = (r_pos + i) % m
            pairs.append((a, b))
        rounds.append(pairs)
        r_pos = (r_pos + step) % m
    return rounds


def _pair_rounds(n_teams: int) -> list[list[tuple[int, int]]]:
    raw = _single_leg_pairs(n_teams)
    order = list(range(len(raw)))
    if len(order) >= 2:
        order[-1], order[-2] = order[-2], order[-1]
    leg1 = [raw[i] for i in order]
    leg2 = [[(b, a) for (a, b) in rnd] for rnd in leg1]
    return leg1 + leg2


def round_count(n_teams: int) -> int:
    return 2 * (n_teams - 1)


# --- Stück-4-Wiederverwendung: break-optimaler Spielplan als TTP-Startpunkt/naive Politik ---


def naive_schedule(n_teams: int, time_limit_s: float = 10.0) -> Schedule:
    """Stück 4s CP-SAT-Break-Minimierung auf der Zirkelmethode-Paarstruktur - nachweislich immer
    gueltig fuer die TTP-Regeln (kein Wiederholungsspiel, max. 3 Runden gleicher Status), aber komplett
    ohne Ruecksicht auf Distanz. Dient als Startpunkt der lokalen Suche und als "naive" Vergleich."""
    all_rounds = _pair_rounds(n_teams)
    n_rounds = len(all_rounds)
    teams = list(range(n_teams))

    model = cp_model.CpModel()
    home = {(t, r): model.NewBoolVar(f"h_{t}_{r}") for t in teams for r in range(n_rounds)}
    pair_rounds: dict[frozenset, list[int]] = {}
    for r, pairs in enumerate(all_rounds):
        for (a, b) in pairs:
            model.Add(home[a, r] + home[b, r] == 1)
            pair_rounds.setdefault(frozenset((a, b)), []).append(r)
    for pair, rs in pair_rounds.items():
        a, _b = tuple(pair)
        r1, r2 = rs
        model.Add(home[a, r1] + home[a, r2] == 1)

    breaks = []
    for t in teams:
        for r in range(1, n_rounds):
            bv = model.NewBoolVar(f"brk_{t}_{r}")
            model.Add(home[t, r] - home[t, r - 1] == 0).OnlyEnforceIf(bv)
            model.Add(home[t, r] - home[t, r - 1] != 0).OnlyEnforceIf(bv.Not())
            breaks.append(bv)
    model.Minimize(sum(breaks))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    # NUR 1 Worker (nicht NUM_SEARCH_WORKERS): das Break-Minimum hat i.d.R. mehrere gleich gute
    # Loesungen (einzelnes Zielkriterium), und WELCHE davon zurueckkommt, wird als Startpunkt der
    # lokalen Suche weiterverwendet UND direkt als "naive" Distanz angezeigt/getestet - die Wahl
    # kaskadiert also, anders als bei solve_exact()s einmaligem Anzeige-Wert. Ein zuerst versuchter
    # lexikografischer Zweit-Term (Gewicht je home[t,r]) loeste das NICHT zuverlaessig: da die
    # Gewichte keine Zweierpotenzen sind, koennen verschiedene Teilmengen densel­ben Summenwert
    # ergeben (Teilmengensumme-Kollision) - bei n=8/12 blieb messbare Resteindeutigkeit aus.
    # Zweierpotenz-Gewichte waeren injektiv, sprengen aber ab ~20 Variablen den int64-Bereich.
    # Sequenzielle Suche (1 Worker) ist dagegen unabhaengig vom Zielkriterium deterministisch
    # (kein Thread-Wettlauf) - gemessen (n=8/12/16, je 3 Wiederholungen): exakt reproduzierbar.
    # Kosten: bis zu time_limit_s Wartezeit bei groesserem n (siehe Spinner in app.py) - siehe project
    # memory zum CP-SAT-Lexikografischen-Gleichstand (dritte Wiederholung, genau dieser Kaskaden-Fall).
    solver.parameters.num_search_workers = 1
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(f"Break-Minimierung fand keine Lösung (status={status})")

    rounds = []
    for r, pairs in enumerate(all_rounds):
        matches = []
        for (a, b) in pairs:
            a_home = solver.Value(home[a, r]) == 1
            matches.append(Match(home=a, away=b) if a_home else Match(home=b, away=a))
        rounds.append(Round(matches=tuple(matches)))
    return Schedule(n_teams=n_teams, rounds=tuple(rounds))


# --- Gueltigkeit + Distanz ---


def is_valid(schedule: Schedule, u_max: int = U_MAX_DEFAULT) -> tuple[bool, str]:
    n = schedule.n_teams
    n_rounds = round_count(n)
    if len(schedule.rounds) != n_rounds:
        return False, f"{len(schedule.rounds)} statt {n_rounds} Runden"

    seen_ordered = set()
    for r, rnd in enumerate(schedule.rounds):
        teams_in_round = set()
        for m in rnd.matches:
            if m.home in teams_in_round or m.away in teams_in_round:
                return False, f"Runde {r}: Team mehrfach"
            teams_in_round.add(m.home)
            teams_in_round.add(m.away)
            if (m.home, m.away) in seen_ordered:
                return False, f"({m.home},{m.away}) mehrfach"
            seen_ordered.add((m.home, m.away))
        if teams_in_round != set(range(n)):
            return False, f"Runde {r}: nicht alle Teams"
    if len(seen_ordered) != n * (n - 1):
        return False, "nicht jedes Paar genau 1x je Seite"

    for r in range(n_rounds - 1):
        pairs_r = {frozenset((m.home, m.away)) for m in schedule.rounds[r].matches}
        pairs_r1 = {frozenset((m.home, m.away)) for m in schedule.rounds[r + 1].matches}
        if pairs_r & pairs_r1:
            return False, f"Wiederholungsspiel Runde {r}->{r+1}"

    home_status = {t: [] for t in range(n)}
    for rnd in schedule.rounds:
        is_home = {t: False for t in range(n)}
        for m in rnd.matches:
            is_home[m.home] = True
        for t in range(n):
            home_status[t].append(is_home[t])
    for t in range(n):
        streak = 1
        for r in range(1, n_rounds):
            if home_status[t][r] == home_status[t][r - 1]:
                streak += 1
                if streak > u_max:
                    return False, f"Team {t}: {streak} gleiche Runden in Folge"
            else:
                streak = 1
    return True, ""


def total_distance(schedule: Schedule, scenario: Scenario) -> float:
    n = schedule.n_teams
    D = scenario.distances
    total = 0.0
    for t in range(n):
        loc = t
        for rnd in schedule.rounds:
            home_match = next((m for m in rnd.matches if m.home == t or m.away == t), None)
            new_loc = t if home_match.home == t else home_match.home
            total += D[loc][new_loc]
            loc = new_loc
        total += D[loc][t]
    return total


# --- Lokale Suche (Anagnostopoulos et al. 2003: SwapHomes, SwapRounds, SwapTeams) ---


def _swap_homes(schedule: Schedule, i: int, j: int) -> Schedule:
    rounds = []
    for rnd in schedule.rounds:
        matches = []
        for m in rnd.matches:
            if (m.home, m.away) == (i, j):
                matches.append(Match(home=j, away=i))
            elif (m.home, m.away) == (j, i):
                matches.append(Match(home=i, away=j))
            else:
                matches.append(m)
        rounds.append(Round(matches=tuple(matches)))
    return Schedule(n_teams=schedule.n_teams, rounds=tuple(rounds))


def _swap_rounds(schedule: Schedule, r1: int, r2: int) -> Schedule:
    rounds = list(schedule.rounds)
    rounds[r1], rounds[r2] = rounds[r2], rounds[r1]
    return Schedule(n_teams=schedule.n_teams, rounds=tuple(rounds))


def _swap_teams(schedule: Schedule, i: int, j: int) -> Schedule:
    def relabel(t):
        return j if t == i else (i if t == j else t)

    rounds = []
    for rnd in schedule.rounds:
        matches = tuple(Match(home=relabel(m.home), away=relabel(m.away)) for m in rnd.matches)
        rounds.append(Round(matches=matches))
    return Schedule(n_teams=schedule.n_teams, rounds=tuple(rounds))


def local_search(
    scenario: Scenario,
    start: Schedule,
    iters: int = 8000,
    seed: int = 0,
    u_max: int = U_MAX_DEFAULT,
) -> tuple[Schedule, float]:
    rng = random.Random(seed)
    n = scenario.n_teams
    n_rounds = round_count(n)

    cur = start
    cur_cost = total_distance(cur, scenario)
    best, best_cost = cur, cur_cost

    t0 = max(cur_cost * 0.02, 1.0)
    t1 = 0.001
    for it in range(iters):
        temperature = t0 * (t1 / t0) ** (it / max(iters, 1))
        move = rng.choice(("homes", "rounds", "teams"))
        if move == "homes":
            i, j = rng.sample(range(n), 2)
            cand = _swap_homes(cur, i, j)
        elif move == "rounds":
            r1, r2 = rng.sample(range(n_rounds), 2)
            cand = _swap_rounds(cur, r1, r2)
        else:
            i, j = rng.sample(range(n), 2)
            cand = _swap_teams(cur, i, j)

        ok, _reason = is_valid(cand, u_max=u_max)
        if not ok:
            continue
        cand_cost = total_distance(cand, scenario)
        if cand_cost < cur_cost or rng.random() < math.exp(-(cand_cost - cur_cost) / max(temperature, 1e-9)):
            cur, cur_cost = cand, cand_cost
            if cur_cost < best_cost:
                best, best_cost = cur, cur_cost
    return best, best_cost


# --- Exaktes CP-SAT-Modell (kleine n) ---


def solve_exact(
    scenario: Scenario, u_max: int = U_MAX_DEFAULT, time_limit_s: float = 20.0
) -> tuple[Schedule | None, float | None, bool]:
    """Volles TTP-Modell (x[i,j,r] = i ist Heim gegen j in Runde r) ohne Einschraenkung auf eine feste
    Paarstruktur - im Gegensatz zu naive_schedule/local_search wird hier der GESAMTE Spielplan frei
    gesucht. Nur fuer kleine n praktikabel (siehe README: ab n=6 meist nicht mehr bewiesen optimal).
    Liefert (None, None, False), wenn CP-SAT innerhalb von time_limit_s nicht einmal eine GUELTIGE
    Loesung findet (nicht nur "nicht bewiesen optimal") - bei groesserem n real beobachtet, ein
    eigenes Symptom der TTP-Schwierigkeit."""
    n = scenario.n_teams
    D = scenario.distances
    n_rounds = round_count(n)
    teams = list(range(n))

    model = cp_model.CpModel()
    x = {}
    for i in teams:
        for j in teams:
            if i == j:
                continue
            for r in range(n_rounds):
                x[i, j, r] = model.NewBoolVar(f"x_{i}_{j}_{r}")

    for i in teams:
        for r in range(n_rounds):
            model.Add(
                sum(x[i, j, r] for j in teams if j != i) + sum(x[j, i, r] for j in teams if j != i) == 1
            )
    for i in teams:
        for j in teams:
            if i != j:
                model.Add(sum(x[i, j, r] for r in range(n_rounds)) == 1)
    for i in teams:
        for j in teams:
            if i < j:
                for r in range(n_rounds - 1):
                    model.Add(x[i, j, r] + x[j, i, r] + x[i, j, r + 1] + x[j, i, r + 1] <= 1)

    home = {}
    for i in teams:
        for r in range(n_rounds):
            home[i, r] = model.NewBoolVar(f"home_{i}_{r}")
            model.Add(home[i, r] == sum(x[i, j, r] for j in teams if j != i))
    for i in teams:
        for r0 in range(n_rounds - u_max):
            window = range(r0, r0 + u_max + 1)
            model.Add(sum(home[i, r] for r in window) <= u_max)
            model.Add(sum(1 - home[i, r] for r in window) <= u_max)

    city = {}
    for i in teams:
        for r in range(n_rounds):
            city[i, r] = model.NewIntVar(0, n - 1, f"city_{i}_{r}")
            model.Add(city[i, r] == i * home[i, r] + sum(j * x[j, i, r] for j in teams if j != i))

    scale = 1000
    max_d = max(max(row) for row in D)
    # Aufrunden als obere Schranke, nicht abschneiden - siehe Vorab-Messreihe: Abschneiden kann das
    # Modell durch Gleitkomma-Rundung faelschlich unerfuellbar machen.
    cost_ub = int(math.ceil(max_d * scale)) + 1
    table = [(a, b, int(round(D[a][b] * scale))) for a in teams for b in teams]

    cost_vars = []
    for i in teams:
        c0 = model.NewIntVar(0, cost_ub, f"c0_{i}")
        model.AddElement(city[i, 0], [int(round(D[i][b] * scale)) for b in teams], c0)
        cost_vars.append(c0)
        for r in range(n_rounds - 1):
            c = model.NewIntVar(0, cost_ub, f"c_{i}_{r}")
            model.AddAllowedAssignments([city[i, r], city[i, r + 1], c], table)
            cost_vars.append(c)
        cend = model.NewIntVar(0, cost_ub, f"cend_{i}")
        model.AddElement(city[i, n_rounds - 1], [int(round(D[a][i] * scale)) for a in teams], cend)
        cost_vars.append(cend)
    model.Minimize(sum(cost_vars))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers = NUM_SEARCH_WORKERS
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Bei kleinen Ligen (n<=6) selten, ab ~n=14-16 real beobachtet: CP-SAT findet innerhalb des
        # Zeitlimits nicht einmal EINE gueltige Loesung (nicht nur "nicht bewiesen optimal") - ein
        # eigenes, ehrliches Symptom der TTP-Schwierigkeit, kein Programmierfehler. Kein Absturz - der
        # Aufrufer (App/Auswertung) zeigt das als eigenen Befund, nicht als Fehler.
        return None, None, False

    rounds = []
    for r in range(n_rounds):
        matches = []
        for i in teams:
            for j in teams:
                if i != j and solver.Value(x[i, j, r]) == 1:
                    matches.append(Match(home=i, away=j))
        rounds.append(Round(matches=tuple(matches)))
    schedule = Schedule(n_teams=n, rounds=tuple(rounds))
    return schedule, solver.ObjectiveValue() / scale, status == cp_model.OPTIMAL
