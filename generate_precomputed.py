"""Erzeugt precomputed_sweep.json einmalig (Build-Zeit) - die 📐/🔬-Sweeps ueber mehrere Teamzahlen
brauchen bis zu mehreren Minuten (mehrere CP-SAT-Loesungen je 20s), das darf nicht bei jedem
Seitenaufruf live laufen. Nach jeder Aenderung an ttp_constants.SWEEP_N_VALUES / CP_SAT_SWEEP_N_VALUES /
den Verfahren selbst neu ausfuehren: `python generate_precomputed.py`.
"""

import json
import time

import ttp_constants as C
from ttp_evaluation import cp_sat_scaling, sweep_methods

if __name__ == "__main__":
    t0 = time.time()
    print("Berechne Sweep (naiv/lokale Suche, ohne CP-SAT)...")
    sweep = sweep_methods(C.SWEEP_N_VALUES, run_cp_sat=False)

    print("Berechne Sweep mit CP-SAT (kleine Ligen)...")
    sweep_cp_sat = sweep_methods(
        C.CP_SAT_SWEEP_N_VALUES, run_cp_sat=True, cp_sat_time_limit_s=C.CP_SAT_SWEEP_TIME_LIMIT_S
    )

    print("Berechne CP-SAT-Skalierung...")
    scaling = cp_sat_scaling(C.CP_SAT_SWEEP_N_VALUES, time_limit_s=C.CP_SAT_SWEEP_TIME_LIMIT_S)

    data = {
        "sweep": [
            {"n_teams": c.n_teams, "naive_distance": c.naive_distance, "local_search_distance": c.local_search_distance}
            for c in sweep
        ],
        "sweep_cp_sat": [
            {
                "n_teams": c.n_teams,
                "naive_distance": c.naive_distance,
                "local_search_distance": c.local_search_distance,
                "cp_sat_distance": c.cp_sat_distance,
                "cp_sat_is_proven": c.cp_sat_is_proven,
            }
            for c in sweep_cp_sat
        ],
        "cp_sat_scaling": [
            {"n_teams": p.n_teams, "seconds": p.seconds, "is_proven": p.is_proven, "distance": p.distance}
            for p in scaling
        ],
    }
    with open("precomputed_sweep.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"precomputed_sweep.json geschrieben ({time.time()-t0:.1f}s)")
