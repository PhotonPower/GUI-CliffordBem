# 02 Plugin-Leitfaden

Ein Plugin ist eine Klasse mit `id`, `label`, `description`, `fields` und den Methoden seiner Art. Module in `cbgui/plugins/` werden
automatisch importiert (`registry.load_plugins`); Pakete Dritter melden sich über die Entry-Point-Gruppe `cbgui.plugins`.

**Regeln:** Beim Import nur Standardbibliothek und numpy (ADR 0001). `cliffordbem` bekommt der Worker als Argument `cb`. Alle `p`
sind Dictionaries mit Anzeigewerten (nm, °), vollständig mit Standardwerten gefüllt. Fähigkeiten, die das Plugin braucht, stehen in
`requires = ("curved",)` und optional `min_version = "0.47"`; fehlen sie, zeigt die GUI das Plugin als nicht verfügbar.

## Felder

```python
Field(key, label, kind="float|int|choice|bool|text|file", default, unit="nm", min=None, max=None, step=None,
      choices=((wert, bezeichnung), ...), help="", advanced=False, visible_if=lambda v: ..., format="%.3f")
```

Das Schema erzeugt Formular, Bereichsprüfung (`Schema.errors`) und Standardwerte. `advanced=True` landet im Expander „Erweitert“.

## Geometrie (`base.Geometry`)

| Mitglied | Zweck |
|---|---|
| `reference_length(p)` | Bezugslänge in nm (Radius, halbe Kante); Längeneinheit der Bibliothek und Q-Normierung |
| `bounding_radius(p)`, `has_sharp_edges(p)` | Prüfungen (Überlappung, Resonanzfenster) |
| `n_elements(p)`, `element_size(p)` | Kosten, Netz gegenüber Wellenlänge |
| `preview(p)` | numpy-Dreiecksnetz (nm) für die 3D-Vorschau, ohne Bibliothek |
| `section(p, plane, offset)` | Umrisse für Nahfeldkarten (optional) |
| `build(cb, p, unit_nm, curved)` | Worker: Netz **um den Ursprung** in Einheiten von `unit_nm` (`cb.TriangleMesh` bzw. `cb.QuadraticMesh`) |
| `supports_curved`, `can_curve(p)` | gekrümmte Elemente möglich |
| `prepare(cb, p)` | Worker: Parameter mit Bibliotheksangaben ergänzen (Gmsh-Datei einlesen) |
| `is_sphere`, `mie_radius(p)` | Mie-Referenz |
| `resolution_key`, `resolution_presets` | Schnelleinstellung „Entwurf/Standard/Fein“ |

### Beispiel: Zylinder-Gerüst

```python
@GEOMETRIES.register
class Cylinder(Geometry):
    id = "cylinder"; label = "Zylinder"
    fields = (Field("radius", "Radius", "float", 20.0, "nm", min=1), Field("height", "Höhe", "float", 60.0, "nm", min=1),
              Field("n", "Netzfeinheit", "int", 6, min=2))
    def reference_length(self, p): return max(p["radius"], p["height"] / 2)
    def n_elements(self, p): ...
    def element_size(self, p): ...
    def preview(self, p): ...                       # numpy
    def build(self, cb, p, unit_nm, curved=False):
        # z. B. Gmsh-Netz erzeugen und mit cb.read_gmsh einlesen, oder cb.TriangleMesh(points, triangles)
        ...
```

## Material (`base.Material`)

`eps(cb, p, lam_nm) -> complex` (Worker, e^{−iωt}: Im ε > 0), optional `eps_numpy` (ohne Bibliothek, für Vorschau und Prüfungen),
`lambda_range(p, caps)`, `validate`, `short`. Für die Schnellauswahl: Eintrag in `plugins/materials.PRESETS`.

## Anregung (`base.Excitation`)

`build(cb, p, outer) -> Incident`. Ebene Welle: `Incident("plane_wave", d, p)`. Quellen und Strahlen: `Incident("field", field=cb.…)` und
`kind = "source"`; die Formulierung muss `solve` dafür erweitern (`ProblemHandle.solve` wirft sonst `NotImplementedError`).
Weitere: `wavelength(p)`, `direction(p)` (Pfeil), `is_circular(p)`, `validate(p, model)`.

## Formulierung (`base.Formulation`)

`make_handle(cb, session, lam_nm) -> ProblemHandle`; `element`, `unknowns_per_element`, `cost_reference`, `cost_exponent`,
`supports(geometry, gp)`. Die Session liefert `meshes`, `flat_meshes`, `media(λ)`, `outer(λ)`, `unit_nm`.
`ProblemHandle`: `solve`, `near_field`, `force_on_body`, `force_far_field`, `body_surfaces`, `unknowns`, `hmatrix_bytes`, `build_seconds`.

## Auswertung (`base.Observable`)

| Mitglied | Prozess | Zweck |
|---|---|---|
| `validate(p, model)` | GUI, Worker | Issues |
| `wavelengths(p, model)` | GUI | Wellenlängen für Prüfungen |
| `n_builds`, `n_solves` | GUI | Kostenmodell |
| `compute(session, p)` | Worker | Dictionary aus Arrays/Zahlen/Strings (keine Objekte) |
| `figures(data, ctx, view)` | GUI | Plotly-Abbildungen aus den Daten, ohne Bibliothek |
| `view_fields` | GUI | Bedienelemente der Ergebnisansicht (Log-Skala, …) |
| `summary(data)`, `details(data)`, `csv(data)` | GUI | Kennzahlen, Tabelle, Export |

Mie-Konvention: Daten tragen `mie_radius_nm` (NaN = keine Referenz), `host_n`, `eps0_re/im` (`_common` in `observables.py`).

## Prüfliste für ein neues Plugin

1. Standardwerte bestehen `Schema.errors` (`test_every_plugin_has_valid_defaults` prüft das automatisch).
2. Geometrie: `preview` geschlossen und plausibel, `n_elements` stimmt mit dem echten Netz überein (Bibliothekstest).
3. Neue Bibliotheksaufrufe in `docs/05_bibliotheksschnittstelle.md` mit Version eintragen, Fähigkeit in `worker.FEATURE_PROBES`.
4. Eintrag in `cbgui/roadmap.py` auf „done“ setzen; `CHANGELOG.md` ergänzen.
5. Test gegen eine unabhängige Referenz (Mie, Summenregel, Symmetrie) mit Marker `library`.
