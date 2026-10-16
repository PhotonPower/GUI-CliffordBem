# 04 Tests

```bash
pytest -m "not library"      # ohne Bibliothek: Kern, Prüfungen, Mie, Store, UI (Sekunden)
pytest                       # mit Bibliothek (CBGUI_WORKER_PYTHONPATH, CBEM_DATA_DIR): etwa eine Minute auf einem Kern
```

Der Marker `library` steht in `tests/test_library.py`; ohne erreichbare Bibliothek überspringt die Fixture `lib_caps` diese Tests
(grün mit Hinweis statt Fehler). Jeder Test bekommt einen eigenen Datenordner (`CBGUI_HOME`, Fixture `_home`).

| Datei | Prüft |
|---|---|
| `test_core.py` | Schema, Registry und Fähigkeitsprüfung, Standardwerte aller Plugins, Geometrie-Vertrag (Vorschau, Elementzahlen), Materialien und Vorzeichen, Konfiguration/Migration, `resolve`, Anregungsbasis |
| `test_checks_cost.py` | jede Prüfregel (Überlappung, Spalt, gekrümmt+Würfel, chirales Medium, Materialbereich, Netz/λ, Resonanzfenster, Speicher, Plugin nicht verfügbar), Kostenmodell gegen die Referenzwerte der Bibliotheksdoku |
| `test_mie_store.py` | Mie (verlustfrei: ext = sca, Rayleigh-Grenze, Gold gegen CliffordBem), Status atomar, Absturzerkennung, Laufverzeichnisse |
| `test_ui.py` | AppTest: jede Seite rendert, Radius ändern, Formwechsel (kein geerbtes n), Dimer-Assistent, Auswertung zuschalten, Startsperre bei Fehlern |
| `test_library.py` | Polarisationsbasis gleich der Bibliothek; Kugel gegen Mie (eben n = 8 < 2 %, gekrümmt n = 3 < 0,3 %); alle Auswertungen, Kraft-Normierung (Querkräfte null, Spannungstensor gegen Impulsbilanz < 3 %); CD chiral ≠ 0, achiral ≈ 0; Orientierungsmittelung der Kugel; Dimer-Anziehung; Gmsh 2. Ordnung gegen Mie; Überlappung im Worker abgelehnt; alle Vorlagen mit Abbildungen |

## Regeln für neue Tests

- Gegen eine **unabhängige Referenz** prüfen (Mie, Summenregel, Symmetrie, Impulsbilanz), nicht gegen einen früheren Lauf.
- Kleine Netze (n = 2–4); Toleranzen aus den Konvergenzordnungen ableiten (eben O(h²), gekrümmt O(h⁴)).
- UI-Tests rufen `Seite.render()` über `AppTest.from_string` auf; Widgets sucht man über die Beschriftung (`label.startswith`).

## Kalibrierung des Kostenmodells

`cost.py` skaliert die Messwerte aus `docs/results_performance.md` der Bibliothek (Referenz je Formulierung bei 1 280 Elementen:
`Formulation.cost_reference`). Der Worker schreibt je Lauf `summary.json` mit `timings`, `unknowns`, `elements`, `peak_rss_mb`,
`threads`. Nachführen: Läufe verschiedener Größe sammeln, Speicher gegen `elements` und Aufbauzeit je Wellenlänge gegen `elements`
auftragen, Referenzwerte und Exponenten in `plugins/formulations.py` anpassen. Stand 0.1: nur an 180–1 280 Elementen auf einem Kern
gegengeprüft (Faktor 2).

## Stand der Prüfung (0.1)

65 Tests, davon 14 mit Bibliothek. Nicht geprüft: Windows/MSYS2, Streamlit-Versionen außer der aktuellen (≥ 1.40 verlangt),
Läufe über 20 000 Elemente, Mehrkern-Skalierung des Kostenmodells.
