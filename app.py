"""Traveling Tournament Problem - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Fünftes Stück der "Turnierplanung"-Linie der "Konzepte"-Reihe: anders als Stück 4 (Heim/Auswärts für
eine FESTE Paarstruktur optimieren) ist hier der GANZE Spielplan frei - welches Team wann gegen wen,
plus Heim/Auswärts, um die Gesamt-Reisedistanz zu minimieren. Ein berühmtes, echtes NP-schweres
Problem der OR-Literatur (Easton, Nemhauser & Trick 2001).

Lauffähig mit: streamlit run app.py
"""

import streamlit as st

import ttp_constants as C
from ttp_evaluation import load_precomputed
from ttp_presets import (
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    sync_query_params,
)
from ttp_scenario import generate_scenario
from ttp_scheduler import local_search, naive_schedule, solve_exact, total_distance
from ttp_visualization import build_comparison_chart, build_cp_sat_scaling_chart, build_route_map

st.set_page_config(page_title="Traveling Tournament Problem – Sebastian Hanisch", layout="wide")


@st.cache_data(show_spinner=False)
def _naive(n_teams):
    return naive_schedule(n_teams)


@st.cache_data(show_spinner=False)
def _local_search(n_teams, seed):
    scenario = generate_scenario(n_teams, seed)
    start = _naive(n_teams)
    best, best_cost = local_search(scenario, start, iters=C.LS_ITERS, seed=C.LS_SEED)
    return best, best_cost


@st.cache_data(show_spinner=False)
def _cp_sat(n_teams, seed):
    scenario = generate_scenario(n_teams, seed)
    schedule, dist, is_proven = solve_exact(scenario, time_limit_s=C.CP_SAT_LIVE_TIME_LIMIT_S)
    return schedule, dist, is_proven


@st.cache_data(show_spinner=False)
def _precomputed():
    # NIE live nachrechnen (mehrere CP-SAT-Loesungen je bis zu 20s) - siehe generate_precomputed.py
    return load_precomputed()


st.title("✈️ Traveling Tournament Problem")
st.markdown(
    """
Bei einer Doppelrunden-Liga (Stück 4) legten wir eine feste Paarstruktur zugrunde und optimierten nur,
**wer wann zuhause spielt**. Beim **Traveling Tournament Problem (TTP)** ist zusätzlich der ganze
Spielplan frei - welches Team wann gegen wen antritt - mit dem Ziel, die **Gesamt-Reisedistanz** aller
Teams zu minimieren. Ein Team ohne einen einzigen Break (Stück 4) kann trotzdem quer durchs Land
pendeln müssen, wenn die Reihenfolge seiner Auswärtsspiele geografisch ungünstig ist.
"""
)
st.caption(
    "Easton, Nemhauser & Trick (2001) haben das Problem anhand der US-Baseball-Liga MLB formuliert - "
    "es gilt seither als eines der schwierigsten kombinatorischen Probleme der Sportplanungs-Literatur, "
    "schwierig selbst für kleine Teamzahlen. Diese Demo zeigt genau das: anders als Stück 4 (CP-SAT löst "
    "bis 50 Teams in Sekunden) stößt CP-SAT hier schon bei kleinen Ligen an seine Grenze."
)

with st.expander("Drei Verfahren im Vergleich", expanded=True):
    st.markdown(
        """
1. **naiv**: Stück 4s break-optimaler Spielplan (Zirkelmethode-Paarstruktur, CP-SAT-optimales
   Heim/Auswärts für Break-Minimierung) - gültig, aber komplett distanzblind.
2. **Lokale Suche**: Standardzüge der TTP-Literatur (Anagnostopoulos, Michel, Van Hentenryck & Vergados
   2003) - SwapHomes, SwapRounds, SwapTeams - startet vom naiven Spielplan, sucht mit
   Simulated-Annealing-Akzeptanz nach kürzeren Touren.
3. **CP-SAT**: das volle TTP-Modell, ohne Einschränkung auf eine feste Paarstruktur - findet für sehr
   kleine Ligen das bewiesene Optimum, für größere oft nur eine unbewiesene obere Schranke.
        """
    )

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_cols = st.columns(len(C.PRESETS))
for i, name in enumerate(C.PRESETS.keys()):
    with preset_cols[i]:
        st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    n_teams = st.slider(
        "Teamzahl", *bounds("n_teams_slider"), step=C.N_TEAMS_STEP, key="n_teams_slider",
        help="Nur gerade Teamzahl, wie in Stück 4.",
    )
    seed = st.slider("Karten-Saatwert", *bounds("seed_slider"), key="seed_slider",
                      help="Bestimmt die zufälligen Heimatstädte auf der Karte.")
    method = st.radio("Verfahren", C.METHODS, key="method_radio")

sync_query_params(n_teams, seed, method)

n_teams = int(n_teams)
seed = int(seed)
scenario = generate_scenario(n_teams, seed)

cp_sat_not_proven_warning = None
cp_sat_no_solution_warning = None
if method == "CP-SAT (kleine Ligen)":
    with st.spinner(f"CP-SAT sucht das Optimum (bis {C.CP_SAT_LIVE_TIME_LIMIT_S:.0f}s)…"):
        schedule, distance, is_proven = _cp_sat(n_teams, seed)
    if schedule is None:
        # Bei groesserem n real beobachtet: CP-SAT findet nicht einmal EINE gueltige Loesung im
        # Zeitbudget - ein eigenes, ehrliches Symptom der TTP-Schwierigkeit (siehe README). Fallback auf
        # den naiven Spielplan, damit die Seite trotzdem etwas zeigt, klar als Notloesung markiert.
        cp_sat_no_solution_warning = (
            f"CP-SAT hat innerhalb von {C.CP_SAT_LIVE_TIME_LIMIT_S:.0f}s nicht einmal eine gültige Lösung "
            "gefunden (nicht nur \"nicht bewiesen optimal\") - ein eigenes Symptom davon, wie schwer das "
            "TTP schon bei mittleren Ligagrößen ist. Gezeigt wird ersatzweise der naive Spielplan."
        )
        with st.spinner("Stück 4s Break-Minimierung läuft (kann bis zu 10s dauern)…"):
            schedule = _naive(n_teams)
        distance = total_distance(schedule, scenario)
    elif not is_proven:
        cp_sat_not_proven_warning = (
            f"CP-SAT hat innerhalb von {C.CP_SAT_LIVE_TIME_LIMIT_S:.0f}s keine bewiesene Optimallösung "
            "gefunden - gezeigt wird die beste bisher gefundene (obere Schranke), nicht das garantierte Optimum."
        )
elif method == "Lokale Suche":
    with st.spinner("Lokale Suche läuft (startet mit Stück 4s Break-Minimierung, kann bis zu 10s dauern)…"):
        schedule, distance = _local_search(n_teams, seed)
else:
    with st.spinner("Stück 4s Break-Minimierung läuft (kann bis zu 10s dauern)…"):
        schedule = _naive(n_teams)
    distance = total_distance(schedule, scenario)

n_rounds = len(schedule.rounds)

st.markdown("---")
st.markdown("## 🎯 Saisonverlauf: die Reiseroute eines Teams")
st.caption(f"{n_teams} Teams, {n_rounds} Runden, Verfahren: **{method}** - Gesamtdistanz: **{distance:,.0f}**.")
if cp_sat_no_solution_warning:
    st.error(cp_sat_no_solution_warning)
elif cp_sat_not_proven_warning:
    st.warning(cp_sat_not_proven_warning)

fcol1, fcol2 = st.columns([2, 3])
with fcol1:
    focus_team = st.selectbox("Team im Fokus", list(range(n_teams)), key="focus_team_select")

round_key = (n_teams, seed, method)
if "round_slider" not in st.session_state or st.session_state.get("round_owner") != round_key:
    st.session_state["round_slider"] = n_rounds
    st.session_state["round_owner"] = round_key

rcol1, rcol2 = st.columns([5, 1])
with rcol1:
    upto_round = st.slider("Bis Runde", 1, n_rounds, key="round_slider")
with rcol2:
    auto_play = st.button("▶️ Abspielen", width="stretch")

map_slot = st.empty()


def _render(r):
    map_slot.plotly_chart(
        build_route_map(scenario, schedule, focus_team, r), width="stretch",
        key=f"map_{n_teams}_{seed}_{method}_{focus_team}_{r}",
    )


if auto_play:
    import time

    for r in range(1, n_rounds + 1):
        _render(r)
        time.sleep(max(0.05, 3.0 / n_rounds))
    upto_round = n_rounds
else:
    _render(upto_round)

st.markdown("---")
st.subheader("📐 Wie viel kostet Distanzblindheit?")
st.markdown(
    "Dieselbe Vergleichsart wie in Stück 4: naiv gegen lokale Suche, über die Teamzahl hinweg. CP-SAT "
    "ist nur für kleine Ligen gezeigt - ab dort ist selbst der Rechenversuch nicht mehr bewiesen optimal."
)
sweep, sweep_cp_sat, cp_sat_scaling_points = _precomputed()
merged = []
cp_sat_by_n = {c.n_teams: c for c in sweep_cp_sat}
for c in sweep:
    if c.n_teams in cp_sat_by_n:
        cp = cp_sat_by_n[c.n_teams]
        merged.append(
            type(c)(
                n_teams=c.n_teams,
                naive_distance=c.naive_distance,
                local_search_distance=c.local_search_distance,
                cp_sat_distance=cp.cp_sat_distance,
                cp_sat_is_proven=cp.cp_sat_is_proven,
            )
        )
    else:
        merged.append(c)
st.plotly_chart(build_comparison_chart(merged), width="stretch", key="comparison_chart")
current = next((c for c in sweep if c.n_teams == n_teams), None)
if current is not None:
    gap = (current.naive_distance - current.local_search_distance) / current.naive_distance * 100
    st.caption(
        f"Bei {n_teams} Teams spart die lokale Suche {gap:.0f}% Reisedistanz gegenüber dem distanzblinden "
        f"Spielplan ({current.naive_distance:,.0f} → {current.local_search_distance:,.0f})."
    )

st.markdown("---")
st.subheader("🔬 Experiment: wo hört CP-SAT auf, beweisbar zu sein?")
scaling = cp_sat_scaling_points
st.plotly_chart(build_cp_sat_scaling_chart(scaling), width="stretch", key="cpsat_scaling_chart")
n_proven = sum(1 for p in scaling if p.is_proven)
st.caption(
    f"Von {len(scaling)} gemessenen Ligagrößen (bis {scaling[-1].n_teams} Teams) fand CP-SAT bei "
    f"{n_proven} das bewiesene Optimum innerhalb von {C.CP_SAT_SWEEP_TIME_LIMIT_S:.0f}s - ganz anders als "
    "Stück 4, wo CP-SAT selbst bei 50 Teams noch in Sekunden bewiesen optimal löste. Das ist der "
    "eigentliche Kernbefund dieses Stücks: derselbe Lösertyp, aber ein strukturell viel schwereres Problem."
)

st.markdown("---")

with st.expander("🚧 Wo die Annahmen enden"):
    st.markdown(
        """
- **Die lokale Suche verändert nie die abstrakte Zirkelmethode-Paarstruktur.** SwapHomes, SwapRounds und
  SwapTeams ändern Heimrecht, Reihenfolge bzw. welches Team welche Stadt bekommt - aber nie, welche
  abstrakten Positionen wann gegeneinander antreten. Das allgemeine TTP erlaubt zusätzlich grundsätzlich
  andere Paarstrukturen; diese Demo durchsucht nur einen (großen, aber eingeschränkten) Teilraum davon.
  CP-SAT durchsucht dagegen den vollen Raum - kommt darin für größere Ligen aber nicht weit genug, um die
  lokale Suche zuverlässig zu schlagen (siehe die 12-Teams-Voreinstellung oben).
- **Nur gerade Teamzahl**, wie in Stück 4.
- **U=3** (höchstens drei gleiche Spiele in Folge) ist der literaturübliche Standardwert (Easton,
  Nemhauser & Trick 2001), hier fest, nicht als Regler.
- **Synthetische Heimatstädte**, kein realer Liga-Bezug - der Mechanismus überträgt sich unverändert auf
  echte Distanzen.
        """
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** $n$ Teams (gerade), Doppelrunde = $2(n-1)$ Runden. Binärvariable $x_{ijr}=1$, wenn Team $i$
in Runde $r$ Heimrecht gegen $j$ hat. Nebenbedingungen: jedes Team spielt genau einmal pro Runde, jedes
geordnete Paar $(i,j)$ genau einmal über die Saison, kein Wiederholungsspiel in Folgerunden, höchstens
$U{=}3$ gleiche Heim-/Auswärtsrunden in Folge (Easton, Nemhauser & Trick 2001). Ziel: Summe der
Reisedistanzen aller Team-Touren (Start/Ende zuhause) minimieren.

**CP-SAT** (`ttp_scheduler.solve_exact`): Standort von Team $i$ nach Runde $r$ als Ganzzahlvariable
$\text{city}_{i,r} = i \cdot h_{i,r} + \sum_j j \cdot x_{jir}$ (eigene Stadt falls Heim, sonst
Gastgeberstadt); Distanzkosten zwischen aufeinanderfolgenden Standorten über eine Tabellen-Nebenbedingung
(`AddAllowedAssignments`), da beide Enden Variablen sind, kein einfacher Lookup.

**Lokale Suche** (`ttp_scheduler.local_search`, nach Anagnostopoulos, Michel, Van Hentenryck & Vergados
2003): SwapHomes (Heimrecht eines Paars tauschen), SwapRounds (zwei Runden vertauschen), SwapTeams
(zwei Teams über die ganze Saison umbenennen) - jeder Zug nur akzeptiert, wenn das Ergebnis weiterhin
alle Nebenbedingungen erfüllt (`ttp_scheduler.is_valid`), mit Simulated-Annealing-Temperaturplan.

Implementiert in `ttp_scheduler.py` (alle drei Verfahren) und `ttp_evaluation.py` (Vergleiche, Sweeps).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zur Reihe: [Turnierplanung: 7 Wege zum Turnierplan](https://sebastianhanisch.net/konzepte-turnierplanung.html)."
)
