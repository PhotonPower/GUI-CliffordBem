# 05 Bibliotheksschnittstelle

Alle Aufrufe von `cliffordbem` stehen in `worker.py`, `gmshinfo.py` und den Worker-Methoden der Plugins. Geprüft gegen
**CliffordBem 0.63.0** (Linux, g++ 13, Python 3.12). Die Namen folgen `docs/python.md` der Bibliothek.

| Zweck | Aufruf | Stelle |
|---|---|---|
| Version, Daten | `cb.__version__`, `cb.DATA_DIR`, `cb.omp_threads()`, `cb.set_num_threads` | `worker.library_info`, `Session` |
| Fähigkeiten | `hasattr` auf `FEATURE_PROBES` (siehe unten) | `worker.library_info` |
| Material | `cb.make_material("Au"\|"Ag"\|Pfad).eps(λ)`, `.lambda_min/.lambda_max` | `Tabulated` |
| Medium | `cb.Medium(eps, mu, chi)` | `Session.media/outer` |
| Netze | `make_icosphere(n, radius)`, `quadratic_icosphere(n, radius)`, `make_cube_uniform(n)`, `make_cube_graded(L)`, `translated(mesh, shift, scale)` (auch `QuadraticMesh`), `read_gmsh(path, scale)` → `[(tag, mesh)]`, `read_gmsh_quadratic` | Geometrien |
| Trennung | `require_separated(a, b, extra, what)` (flache Netze; gekrümmt: `.flat`) | `Session._build_meshes` |
| Probleme | `ScatteringProblem(bodies, media, ω, outer=, hmatrix=)`, `CurvedScatteringProblem(…)`, `.solve_plane_wave(d, p, SolveOptions)`, `.mesh`, `.unknowns`, `.hmatrix_bytes` | `formulations._Handle` |
| Löseroptionen | `SolveOptions(tol, max_iter)`, `HMatrixParams(eps[, eta=2])` | `_Handle` |
| Anregung | `polarization_basis(d)`, `circular_polarization(d, ±1)`, `lebedev(n)` | `PlaneWave`, `Spectrum` |
| Nahfeld | flach `exterior_near_field(mesh, h, medium, ω, d, p, pts)`; gekrümmt `exterior_near_field_curved(…)` → dict `E, H, inside, too_close, enhancement, chirality` | `_Handle.near_field` |
| Kräfte | flach `plane_wave_evaluator`; gekrümmt `PlaneWaveField` + `project_incident_curved` + `near_field_evaluator_curved`; dann `force_on_offset(ev, medium, body_flat, δ)`; flach zusätzlich `force_from_far_field` | `_Handle.force_*` |
| Abstand | `distance_to_surface(mesh, points, rmax)` | `Forces.compute` |

Gleichungen: Streuspur und Normierung wie in der Bibliothek (`docs/results_force.md`: F = σ_pr·½ε|E₀|²).

## Fähigkeitsschlüssel (`worker.FEATURE_PROBES`)

`near_field`, `forces`, `gmsh`, `gmsh_quadratic`, `curved`, `curved_layered`, `layered`, `thin_layer`, `two_port`, `linear`, `dipole`,
`beams`, `custom_fields`, `recycling`, `hodlr`. Neuer Schlüssel = eine Zeile; Plugins nutzen ihn über `requires`.

## Bekannte Grenzen der Bibliothek, die die GUI weitergibt

- Impulsbilanz im Fernfeld nur für ebene Elemente (`force_far_field` liefert bei gekrümmten `None`).
- Chirales Außenmedium: nur zirkulare Polarisation (Prüfung in `PlaneWave.validate` und `Spectrum.validate`).
- Würfel/scharfe Kanten: Resonanzfenster für ε/ε_außen in [−3, −1/3] (Warnung in `checks.py`).
- Materialien werden nicht von der Bibliothek ausgewertet; ε(λ) liefert die GUI je Wellenlänge.
- Eine laufende Rechnung lässt sich nicht kooperativ abbrechen; die GUI beendet den Worker-Prozess.
