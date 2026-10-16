# CLAUDE.md – Arbeitsanleitung für GUI-CliffordBem

Streamlit-Oberfläche für die Bibliothek CliffordBem (C++17, pybind11). Sprache des Projekts: **Deutsch**. Stand: GUI 0.1,
Bibliothek 0.63 (siehe `CHANGELOG.md`).

**Grenze:** Dieses Repository enthält nur die GUI. Das Bibliotheksprojekt `CliffordBem` wird **nicht** verändert; Lücken der
Bibliothek kommen in `docs/backlog.md` (Abschnitt „Wünsche an die Bibliothek“).

## Befehle

```bash
streamlit run app.py
pytest -m "not library"                                          # schnell, ohne Bibliothek
CBGUI_WORKER_PYTHONPATH=<build>/python CBEM_DATA_DIR=<repo>/data/materials pytest     # alles (~1 min)
ruff check . --fix
```

Bibliothek bauen (Linux, ein Kern ~15 min): `cmake -S CliffordBem -B build -DCBEM_BUILD_PYTHON=ON -DCBEM_BUILD_TESTS=OFF
-DCBEM_BUILD_APPS=OFF && cmake --build build -j`.

## Aufbau

```
app.py                   Einstieg, Navigation, Seitenleiste
cbgui/params.py          Field, Schema (Formulare, Bereichsprüfung)
cbgui/registry.py        fünf Registries, Plugin-Entdeckung, Fähigkeitsprüfung (requires, min_version)
cbgui/base.py            Basisklassen der Plugins, Issue, Incident, Solution, ProblemHandle
cbgui/config.py          Konfigurationsdictionary, schema_version, migrate
cbgui/model.py           resolve(cfg) → Model (Plugin-Instanzen, vollständige Parameter, Längeneinheit)
cbgui/checks.py          alle Vorab-Prüfungen   cbgui/cost.py  Kostenmodell
cbgui/worker.py          einziger Ort mit `import cliffordbem`: info, inspect, material_eps, run; Session
cbgui/bridge.py          GUI → Worker (Unterprozess, Dateien)   cbgui/store.py  Run-Verzeichnisse
cbgui/plugins/           geometries, materials, excitations, formulations, observables
cbgui/reference/mie.py   Mie-Referenz   cbgui/gmshinfo.py  Gmsh-Datei prüfen   cbgui/roadmap.py  Fahrplan
cbgui/ui/                state, widgets, preview (3D), nav, pages/*
cbgui/templates/         Beispielvorlagen (JSON)
tests/                   pytest (Marker `library`), AppTest für die Seiten
docs/                    Konzept, Leitfäden, ADRs, Roadmap, Backlog, Handover
```

## Konventionen (Kurzfassung, Einzelheiten `docs/03_konventionen.md`)

- Länge nm, Winkel °, Wellenlänge nm. Die Bibliothek rechnet in einer Einheit L = Bezugslänge des ersten Körpers
  (`Model.unit_nm`); Umrechnung nur in `Session` und `Plugin.build`.
- Zeitkonvention e^{−iωt}: Absorption = Im ε > 0, ε = (n + ik)².
- Plugin-Module: beim Import nur Standardbibliothek und numpy. `cb` wird übergeben.
- Der GUI-Prozess importiert **nie** `cliffordbem` (ADR 0001).
- Widget-Schlüssel immer über `state.wkey(...)` und mit Plugin-Id im Präfix; Ersatz des ganzen Modells nur über `state.set_cfg`
  (erhöht `gen`).
- Ergebnisse einer Auswertung: Dictionary aus Arrays/Zahlen/Strings, keine Objekte (`results.npz`, `allow_pickle=False`).

## Fallstricke

- Streamlit behält den Zustand eines Widgets über seinen Schlüssel; wechselt die Art eines Plugins, müssen die Schlüssel
  wechseln (sonst erbt der Würfel das n der Kugel – Test `test_switch_to_cube_…`).
- Die Bibliothek wertet Materialien nicht selbst aus: ε(λ) kommt aus `Material.eps` im Worker.
- `ProblemHandle` rechnet bei fester Wellenlänge; Spektren bauen je Wellenlänge neu auf (Kosten!). `Session.solve` cached Lösungen
  je Problem; `cmd_run` führt Auswertungen bei einer Wellenlänge zuerst aus, damit sie sich Aufbau und Lösung teilen.
- Kräfte: `F_lib = σ_pr · ½ε|E₀|²` mit |E₀|² = |p|²; Umrechnung nach pN in `Forces.compute`.
- Gmsh: `GmshFile.prepare` prüft die Datei im Worker neu; `_info` aus der GUI ist nur für Vorschau und Prüfungen.

## Wo anfangen

Neue Fähigkeit der Bibliothek: `docs/02_plugin_leitfaden.md`. Übergabestand und offene Punkte: `docs/handover.md`, `docs/backlog.md`.
