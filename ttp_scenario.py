"""Synthetischer Szenario-Generator: n Team-Heimatstaedte als Punkte in der Ebene, euklidische
Distanzmatrix. Kein Fall-Demo-Realweltbezug noetig (Konzepte-Linie) - Seed-gesteuert wie jede andere
Demo im Portfolio."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

MAP_SIZE = 100.0


@dataclass(frozen=True)
class Scenario:
    n_teams: int
    seed: int
    cities: tuple[tuple[float, float], ...]
    distances: tuple[tuple[float, ...], ...]


def generate_scenario(n_teams: int, seed: int) -> Scenario:
    rng = random.Random(seed)
    cities = tuple((rng.uniform(0, MAP_SIZE), rng.uniform(0, MAP_SIZE)) for _ in range(n_teams))
    distances = tuple(
        tuple(math.dist(cities[i], cities[j]) if i != j else 0.0 for j in range(n_teams))
        for i in range(n_teams)
    )
    return Scenario(n_teams=n_teams, seed=seed, cities=cities, distances=distances)
