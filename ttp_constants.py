"""Regler-Grenzen, Presets und Konstanten fuer die TTP-Demo."""

DEFAULT_N_TEAMS = 8
N_TEAMS_MIN, N_TEAMS_MAX, N_TEAMS_STEP = 4, 16, 2

DEFAULT_SEED = 5
SEED_MIN, SEED_MAX = 0, 99

METHODS = ["Lokale Suche", "naiv (Stück 4, distanzblind)", "CP-SAT (kleine Ligen)"]
DEFAULT_METHOD = "Lokale Suche"

LS_ITERS = 8000
LS_SEED = 1
CP_SAT_LIVE_TIME_LIMIT_S = 15.0

SWEEP_N_VALUES = [4, 6, 8, 10, 12, 14, 16]
CP_SAT_SWEEP_N_VALUES = [4, 6, 8, 10, 12]
CP_SAT_SWEEP_TIME_LIMIT_S = 20.0

_BASE = {"n_teams": DEFAULT_N_TEAMS, "seed": DEFAULT_SEED, "method": DEFAULT_METHOD}
PRESETS = {
    "Kleine Liga, alle drei Verfahren gleich gut (4 Teams)": {**_BASE, "n_teams": 4, "method": "CP-SAT (kleine Ligen)"},
    "CP-SAT stoesst an seine Grenze (8 Teams)": {**_BASE, "n_teams": 8, "method": "CP-SAT (kleine Ligen)"},
    "Lokale Suche schlaegt CP-SAT im Zeitbudget (12 Teams)": {**_BASE, "n_teams": 12, "method": "Lokale Suche"},
    "Ohne Distanzbewusstsein (naiv, 10 Teams)": {**_BASE, "n_teams": 10, "method": "naiv (Stück 4, distanzblind)"},
}
PRESET_HELP = {
    "Kleine Liga, alle drei Verfahren gleich gut (4 Teams)": "Bei 4 Teams findet CP-SAT das bewiesene Optimum in Sekundenbruchteilen - alle drei Verfahren liegen hier nah beieinander.",
    "CP-SAT stoesst an seine Grenze (8 Teams)": "Schon bei 8 Teams findet CP-SAT innerhalb des Zeitlimits meist keine bewiesen optimale Loesung mehr - typisch fuer das Traveling Tournament Problem.",
    "Lokale Suche schlaegt CP-SAT im Zeitbudget (12 Teams)": "Bei 12 Teams liefert die lokale Suche oft eine BESSERE Loesung als CP-SAT im gleichen Zeitbudget findet - CP-SAT durchsucht den vollen, viel groesseren Raum, kommt aber nicht weit genug.",
    "Ohne Distanzbewusstsein (naiv, 10 Teams)": "Stück 4s break-optimaler Spielplan ist gueltig, aber komplett distanzblind - die lokale Suche zeigt daneben, wie viel das kostet.",
}
