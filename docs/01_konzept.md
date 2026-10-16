# 01 Konzept und Architektur

## Ziel

Eine Oberfläche, die mit dem heutigen CliffordBem (v0.63) sofort nützlich ist und mit der Bibliothek wächst (Beschichtungen,
Dipole, Strahlen, Server), ohne die Seiten umzuschreiben. Erweiterung = eine Klasse (`docs/02_plugin_leitfaden.md`).

## Prozessmodell

```
 GUI-Prozess (Streamlit, numpy, plotly)                    Worker-Prozess (cliffordbem, numpy)
 ┌─────────────────────────────────────────┐              ┌──────────────────────────────────┐
 │ ui/pages  Modell · Anregung · Auswertung│  Dateien     │ worker.py   info | inspect |     │
 │           Berechnung · Ergebnisse · Läufe│ ───────────► │             material_eps | run   │
 │ checks.py cost.py  Prüfungen, Kosten    │ config.json  │ Session     Netze, Probleme,     │
 │ plugins/  (Formulare, Vorschau, Bilder) │              │             Lösungen, Fortschritt│
 │ bridge.py Unterprozess starten/abbrechen│ ◄─────────── │ plugins/    build, eps, compute  │
 └─────────────────────────────────────────┘ status.json  └──────────────────────────────────┘
                                              results.npz
```

Gründe (ADR 0001): Die Bibliothek kann in einer eigenen Umgebung leben (MSYS2-Build ohne Streamlit); ein Absturz oder
Speichermangel im Löser reißt die GUI nicht mit; ein Fernstart ist derselbe Vertrag mit anderem Startbefehl; die GUI bleibt ohne
Bibliothek bedienbar (Vorschau, Prüfungen) und fragt Fähigkeiten ab statt sie anzunehmen.

Kurze Abfragen (`info`, `inspect`, `material_eps`) laufen über die Worker-Kommandozeile mit JSON in der **letzten** Ausgabezeile
und werden von der GUI zwischengespeichert. `run <run_dir>` ist der lange Auftrag.

## Das Run-Verzeichnis (der Vertrag)

```
<runs_dir>/<JJJJMMTT-HHMMSS>_<name>/
    config.json    vollständiger Datensatz inkl. "resolved" (Bibliotheksfähigkeiten, GUI-Version)
    status.json    queued → building → solving → postprocessing → done | error | cancelled
                   + progress (0…1), message, worker_pid, started/finished, traceback
    results.npz    Arrays obs<i>__<name> (i = Index in config.observables)
    summary.json   Kennzahlen je Auswertung, Zeiten, Spitzenspeicher, Iterationen
    report.txt     lesbarer Bericht inkl. Protokoll      run.log   stdout/stderr
```

`status.json` wird atomar ersetzt (`store.write_status`). `store.live_status` erkennt Abstürze (Prozess weg, Zustand nicht final).

## Datenfluss eines Laufs

1. GUI: `checks.collect_issues` (Fehler sperren „Lauf starten“); `bridge.start_run` schreibt `config.json` und startet den Worker
   abgekoppelt.
2. Worker: Konfiguration laden → `resolve` → `Geometry.prepare` (Dateien frisch prüfen) → erneute Prüfung → `Session` (Netze einmal
   bauen, Körper auf Überlappung prüfen, Anregung bauen).
3. Je Auswertung `compute(session, p)`: `session.problem(λ)` (Formulierung baut das Problem), `session.solve(handle, incident)`.
   Ergebnisse als Arrays; Fortschritt über `session.tick`.
4. Speichern: `results.npz`, `summary.json`, `report.txt`, Zustand `done`.
5. GUI: Ergebnisseite lädt Arrays, `Observable.figures` zeichnet (ohne Bibliothek).

Optimierung: Auswertungen bei einer Wellenlänge laufen zuerst und teilen Problemaufbau und Lösung (Session-Cache); Spektren danach.

## Die fünf Plugin-Arten

| Registry | Aufgabe | GUI-Seite | Worker-Seite |
|---|---|---|---|
| `GEOMETRIES` | Form, Größe, Netzfeinheit | Formular, Vorschau, Elementzahl | `build` (Netz um den Ursprung) |
| `MATERIALS` | ε(λ) | Formular | `eps` |
| `EXCITATIONS` | einfallendes Feld | Formular, Pfeile in der Vorschau | `build` → `Incident` |
| `FORMULATIONS` | Diskretisierung + Problemklasse | Auswahl, Kostenmodell | `make_handle` → `ProblemHandle` |
| `OBSERVABLES` | Größen berechnen und zeichnen | Formular, `figures`, `summary` | `compute` |

`ProblemHandle` ist die Schnittstelle zwischen Formulierung und Auswertung (`solve`, `near_field`, `force_on_body`,
`force_far_field`, `body_surfaces`). Eine neue Formulierung muss nur sie liefern; alle Auswertungen laufen dann mit.

## Modulkarte

| Modul | Aufgabe | Prozess |
|---|---|---|
| `params`, `registry`, `base`, `config`, `model` | Formularschemas, Plugins, Konfiguration, aufgelöstes Modell | beide |
| `checks`, `cost` | Vorab-Prüfungen, Kosten | GUI und Worker |
| `plugins/` | konkrete Plugins | beide |
| `store` | Run-Verzeichnisse | alle |
| `bridge` | Unterprozesse | GUI |
| `worker` | Rechenseite | Worker |
| `reference/mie` | analytische Referenz | beide |
| `ui/` | Seiten, Widgets, Vorschau | GUI |

## Erweiterungspunkte

Neue Form/Material/Anregung/Formulierung/Auswertung: eine Klasse. Neue Bibliotheksfähigkeit: Eintrag in `worker.FEATURE_PROBES`,
`requires` im Plugin. Neue Konfigurationsfelder: `SCHEMA_VERSION` erhöhen, Block in `config.migrate`. Fernrechnen: `bridge.start_run`
und `bridge.worker_argv` ersetzen.
