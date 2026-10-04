# Traveling Tournament Problem

Fünftes Stück der **Turnierplanung**-Linie der "Konzepte"-Reihe von [sebastianhanisch.net](https://sebastianhanisch.net).
Interaktive Demo: `streamlit run app.py`.

**[→ Demo live ausprobieren](https://sebastianhanisch-traveling-tournament-demo.streamlit.app/)**

## Ergebnis in Kürze

Anders als Stück 4 (Heim/Auswärts für eine FESTE Paarstruktur optimieren) ist hier der ganze Spielplan
frei - welches Team wann gegen wen, plus Heim/Auswärts, um die Gesamt-Reisedistanz zu minimieren. Drei
Verfahren im Vergleich (n Teams, synthetische Heimatstädte):

- **naiv** (Stück 4s break-optimaler Spielplan, komplett distanzblind): bei 8 Teams 5.742, bei 12
  Teams 14.664 Distanzeinheiten.
- **Lokale Suche** (SwapHomes/SwapRounds/SwapTeams, Anagnostopoulos et al. 2003): 3.962 bzw. 10.439 -
  **31 % bzw. 29 % weniger** als der distanzblinde Spielplan.
- **CP-SAT** (volles Modell, keine feste Paarstruktur): bei 4 Teams bewiesen optimal in 0,12 s (731,1 -
  exakt was auch die lokale Suche findet). Ab 6 Teams **nicht mehr bewiesen optimal** innerhalb von 20 s;
  bei 14 Teams liefert CP-SAT dabei durchgehend (3 Wiederholungen gemessen, 15.933-16.420) eine
  SCHLECHTERE obere Schranke als die lokale Suche (15.329, deterministisch) im selben Zeitbudget findet.

Das ist der Kernbefund dieses Stücks: anders als Stück 4 (CP-SAT löst bis 50 Teams durchgehend bewiesen
optimal in Sekunden) ist das TTP selbst für kleine Ligen schwer - genau der literaturbekannte Ruf des
Problems (Easton, Nemhauser & Trick 2001).

## Was die Demo zeigt

1. **Wachsendes Beispiel**: die Reiseroute eines wählbaren Teams auf der Karte, Runde für Runde -
   Verfahren per Regler umschaltbar (naiv / Lokale Suche / CP-SAT).
2. **📐 Wie viel kostet Distanzblindheit?**: Sweep über die Teamzahl, naiv gegen lokale Suche, plus
   CP-SAT für kleine Ligen.
3. **🔬 Experiment**: CP-SAT-Skalierungsgrenze - ab welcher Teamzahl hört die Beweisbarkeit auf?
4. **🚧 Wo die Annahmen enden**: die lokale Suche durchsucht nur einen Teilraum (feste
   Zirkelmethode-Struktur), U=3 ist fest, synthetische Städte statt echter Liga.

## Was diese Demo nicht kann

Die lokale Suche verändert nie die abstrakte Zirkelmethode-Paarstruktur (nur Heimrecht, Reihenfolge,
Teamzuordnung) - das allgemeine TTP erlaubt zusätzlich grundsätzlich andere Paarstrukturen. CP-SAT
durchsucht diesen vollen Raum, kommt darin für größere Ligen aber nicht weit genug, um die lokale Suche
zuverlässig zu schlagen - eine ehrliche, gemessene Grenze, keine verdeckte Einschränkung.

## Modell und Verfahren

- **Modell**: $n$ Teams (gerade), Doppelrunde. Binärvariable $x_{ijr}=1$, wenn Team $i$ in Runde $r$
  Heimrecht gegen $j$ hat. Nebenbedingungen (Easton, Nemhauser & Trick 2001): jedes Team spielt genau
  einmal pro Runde, jedes geordnete Paar genau einmal über die Saison, kein Wiederholungsspiel in
  Folgerunden, höchstens $U{=}3$ gleiche Heim-/Auswärtsrunden in Folge. Ziel: Summe der Reisedistanzen
  aller Team-Touren (Start/Ende zuhause) minimieren.
- **naive_schedule** (`ttp_scheduler.py`): Stück 4s Break-Minimierung auf der Zirkelmethode-Paarstruktur,
  ohne Distanzbezug - dient als Startpunkt und Vergleichspolitik.
- **local_search**: SwapHomes (Heimrecht eines Paars tauschen), SwapRounds (zwei Runden vertauschen),
  SwapTeams (zwei Teams über die ganze Saison umbenennen) - jeder Zug nur akzeptiert, wenn das Ergebnis
  weiterhin gültig ist, mit Simulated-Annealing-Temperaturplan.
- **solve_exact**: volles CP-SAT-Modell ohne Einschränkung auf eine feste Paarstruktur - Standort von
  Team $i$ nach Runde $r$ als Ganzzahlvariable $\text{city}_{i,r} = i \cdot h_{i,r} + \sum_j j \cdot
  x_{jir}$, Distanzkosten über eine Tabellen-Nebenbedingung (`AddAllowedAssignments`), da beide Enden
  Variablen sind.
- **Quellen**: Easton, K., Nemhauser, G., & Trick, M. (2001). "The Traveling Tournament Problem
  Description and Benchmarks." *CP 2001*. Anagnostopoulos, A., Michel, L., Van Hentenryck, P., &
  Vergados, Y. (2003). "A Simulated Annealing Approach to the Traveling Tournament Problem." *CP-AI-OR
  2003*.

## Verifikation

- **Strukturell** (`tests/test_scheduler.py`): naiv/lokale Suche/CP-SAT erfüllen für $n=4\dots10$ immer
  die TTP-Grundregeln; CP-SAT bei $n=4$ stimmt exakt mit der lokalen Suche überein (beide bewiesen/de
  facto optimal).
- **Nicht-Determinismus gefunden+gefixt beim Bau**: die erste Fassung von `naive_schedule` nutzte
  mehrere CP-SAT-Suchworker für die Break-Minimierung - da dieses Zielkriterium meist mehrere gleich gute
  Lösungen hat, lieferte das bei jedem Lauf eine ANDERE (aber gleich break-optimale) Lösung mit jeweils
  anderer Reisedistanz. Ein lexikografischer Gleichstand-Tiebreak-Term löste das nicht zuverlässig
  (Gewichte ohne Zweierpotenzen können kollidieren); gefixt durch `num_search_workers=1` speziell für
  diesen Aufruf (sequenzielle Suche ist unabhängig vom Zielkriterium deterministisch) - verifiziert durch
  dreifache Wiederholung bei $n=8/12/16$.
- **Politik-Vergleich** (`tests/test_evaluation.py`, `tests/test_claims.py`): lokale Suche nie schlechter
  als naiv, CP-SAT beweist bei $n=4$ das Optimum, aber nicht mehr zuverlässig bei $n=10$.

## Dateistruktur

```
app.py                Streamlit-Oberfläche
ttp_constants.py       Regler-Grenzen, Presets
ttp_scenario.py         Heimatstädte, Distanzmatrix
ttp_scheduler.py        Drei Verfahren (naiv, lokale Suche, CP-SAT), Gültigkeitsprüfung
ttp_evaluation.py       Vergleiche, Sweeps, Skalierungsmessung
ttp_presets.py          Permalink-Muster
ttp_visualization.py    Plotly-Grafiken (Routenkarte, Vergleich, Skalierung)
tests/                  pytest-Suite
```

## Lokal starten

```bash
python -m venv venv
venv\Scripts\activate  # Windows; unter Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Tests ausführen

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

---

Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). Mehr zur Reihe: [Turnierplanung: 7 Wege zum Turnierplan](https://sebastianhanisch.net/konzepte-turnierplanung.html).
