# 07 Roadmap und Einbaupunkte

Quelle der Bibliothekspläne: `docs/ARCHITECTURE.md` (Ausbauplan) und `CHANGELOG.md` des Projekts CliffordBem. Die App zeigt den Fahrplan
dynamisch (`cbgui/roadmap.py`, Seite „Bibliothek und Fahrplan“) und gleicht ihn mit den Fähigkeiten der Bibliothek ab.

## Umgesetzt in 0.1

Kugel, Würfel, Gmsh, Mehrkörper, chirale Körper und Medien; Au, Ag, n+ik, ε, Drude, YAML; flache und gekrümmte Elemente; ebene Welle;
Extinktion, Spektrum, Nahfeld, Kräfte.

## Als Nächstes (Bibliothek kann es bereits)

| Fähigkeit | Bibliothek | Einbau in die GUI |
|---|---|---|
| **Beschichtete Körper** (Kern-Schale, Mehrfachschichten) | `LayeredScatteringProblem`, `LayeredGeometry.add_coated_body`, gekrümmt `CurvedLayeredScatteringProblem` (v0.62) | Körperfeld `coating`: Liste (Dicke, Material); neue Formulierungen `layered`, `curved_layered` mit eigenem `ProblemHandle` (Netze aller Flächen aus `offset_surface`); `Geometry.build` bleibt |
| **Dünne Schichten** | `ThinLayerScatteringProblem` (Näherung 2. Ordnung), `TwoPortLayerProblem` (beliebige Dicke) | Formulierungen `thin_layer`, `two_port`; Prüfung d/h (Doku: Iterationen wachsen ab d ≳ h); Auswertung „Schichtwirkung“ als Differenz zur neutralen Rechnung |
| **Dipol/Emitter** | `DipoleField`, `dipole_rates`, `fluorescence_enhancement` | Anregung `dipole` (`kind="source"`, Position, Moment, Magnetdipol), `ProblemHandle.solve` für `Incident("field")` über `solve_rhs` + `project_dipole`; Auswertungen `dipole_rates`, `fluorescence` |

## Geplant

| Fähigkeit | Einbau |
|---|---|
| Gauß-, fokussierte, Bessel-/Wirbelstrahlen (`BeamField`, `AngularSpectrumField`) | Anregungs-Plugins; Auswertung Kraft/Nahfeld nutzt den Evaluator mit `Incident("field")` |
| Eigene Felder (`CustomField`) | Anregung „Python-Ausdruck/Datei“ mit `maxwell_residual`-Prüfung vor dem Start |
| Streu- und Absorptionsquerschnitt, Fernfeldmuster | Auswertung mit `far_field_E` auf Lebedev-Gitter; σ_abs = σ_ext − σ_sca |
| Kraftkarten, Emitterkraft, Dipolkraft | Auswertungen mit `force_*`, `fields_with_gradients`, `polarizability_from_mie` |
| Lineare Dichten auf ebenen Elementen | Formulierung `linear` (`LinearScatteringProblem`) |
| Krylov-Recycling, HODLR | Lösereinstellungen im Lauf; `use_recycling` für Mehrfachrichtungen (Spektrum mit Orientierungsmittelung) |
| Serienläufe | „Parameterstudie“ über ein Feld; Worker erhält Liste von Konfigurationen, Archiv gruppiert |
| Fernrechnen | `bridge.start_run`/`worker_argv` ersetzen (ssh oder Warteschlange); Run-Verzeichnis per gemeinsamem Speicher oder Kopie |

## Wartet auf die Bibliothek (Ausbauplan CliffordBem)

Substrate (geschichtete Außenmedien), Streumatrix, Drude-Lorentz-Fits und Größenkorrektur der Dämpfung, Dipolquellen im chiralen Medium
und in Schichten, Dipolkraft im chiralen Medium, Pinzette für Mikrometer-Teilchen, nichtkonforme Kantennetze.
Jeweils: Fähigkeit in `worker.FEATURE_PROBES`, Plugin mit `requires`, Fahrplaneintrag auf „done“.

## Rezept: neue Fähigkeit in fünf Schritten

1. Aufruf in der Bibliothek prüfen (`help(cb.…)`), in `docs/05_bibliotheksschnittstelle.md` eintragen.
2. Fähigkeitsschlüssel in `worker.FEATURE_PROBES`.
3. Plugin schreiben (`docs/02_plugin_leitfaden.md`), `requires` setzen.
4. Test gegen unabhängige Referenz, Fahrplan und CHANGELOG aktualisieren.
5. Falls neue Konfigurationsfelder: `SCHEMA_VERSION` + `migrate`.
