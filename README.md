# GUI-CliffordBem

Streamlit-Oberfläche für die Randelementbibliothek **[CliffordBem](https://github.com/PhotonPower/CliffordBem)**
(koordinatenfreie BEM der Nano-Optik in der Clifford-Algebra Cl₃(ℂ)). Stand: GUI 0.1 gegen Bibliothek **0.63**.

Modellieren, rechnen und auswerten ohne Skripte: Körper und Materialien wählen, Anregung einstellen, Auswertungen ankreuzen,
Vorab-Prüfung lesen, starten, Fortschritt verfolgen, Abbildungen ansehen und exportieren.

## Was sie kann (0.1)

| Bereich | Umfang |
|---|---|
| Körper | Kugel, Würfel (gradiert), Gmsh-Datei (je physikalische Gruppe ein Körper), beliebig viele Körper, Dimer-Assistent, chirale Körper, chirales Außenmedium |
| Material | Au, Ag (Johnson–Christy), n + ik, ε, Drude-Modell, YAML-Datei (refractiveindex.info) |
| Formulierung | konstante Dichten auf ebenen Dreiecken (Standard) · lineare Dichten auf gekrümmten Elementen (O(h⁴), Kugel und Gmsh 2. Ordnung) |
| Anregung | ebene Welle: beliebige Richtung, linear (Winkel ψ) oder zirkular σ₊/σ₋ |
| Auswertung | Extinktion · Spektrum (unpolarisiert, zirkular mit CD, Orientierungsmittelung) · Nahfeldkarte (Verstärkung, optische Chiralität) · optische Kräfte je Körper |
| Komfort | 3D-Vorschau, Vorab-Prüfung mit den Regeln der Bibliotheksdoku, Kostenabschätzung, Fortschritt, Abbruch, Läufe-Archiv, Spektrenvergleich, Mie-Überlagerung, Vorlagen |

Geplantes (beschichtete Körper, Dipole, Strahlen, Server) steht in [`docs/07_roadmap.md`](docs/07_roadmap.md) und auf der Seite
„Bibliothek und Fahrplan“ der App.

## Installation

```bash
git clone https://github.com/PhotonPower/GUI-CliffordBem.git && cd GUI-CliffordBem
python -m venv .venv && . .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Die GUI läuft auch **ohne** Bibliothek (Vorschau, Prüfungen); gerechnet wird, sobald ein Python mit `cliffordbem` erreichbar ist:

| Situation | Einstellung |
|---|---|
| `cliffordbem` im selben Python (`pip install .` im Bibliotheksprojekt) | nichts |
| Bibliothek separat gebaut (`cmake … -DCBEM_BUILD_PYTHON=ON`) | `CBGUI_WORKER_PYTHONPATH=<…>/build/python` |
| Bibliothek in einem anderen Python (z. B. MSYS2 UCRT64) | zusätzlich `CBGUI_WORKER_PYTHON=C:/msys64/ucrt64/bin/python.exe` |
| Materialdaten nicht gefunden | `CBEM_DATA_DIR=<…>/data/materials` |

Weitere Variablen: `CBGUI_HOME` (Datenordner, Standard `~/cbgui_data`), `CBGUI_RUNS_DIR`. Gründe für die Prozesstrennung:
[`docs/adr/0001-prozesstrennung.md`](docs/adr/0001-prozesstrennung.md).

## Erste Schritte

1. App starten, auf der Startseite eine **Vorlage** laden („Goldkugel in Wasser: Spektrum“).
2. Unter **Berechnung** die Prüfung lesen und **Lauf starten**.
3. Unter **Ergebnisse** Spektrum, Mie-Vergleich und Export ansehen.

## Entwicklung

```bash
pip install -e ".[dev]"
pytest -m "not library"                       # ohne Bibliothek, Sekunden
CBGUI_WORKER_PYTHONPATH=…/build/python pytest # alles, etwa eine Minute
ruff check .
```

Einstieg für Mitarbeitende und für Claude: [`CLAUDE.md`](CLAUDE.md), [`CONTRIBUTING.md`](CONTRIBUTING.md), [`docs/README.md`](docs/README.md).

## Lizenz

Siehe [`LICENSE`](LICENSE).
