# 03 Konventionen

## Einheiten und Vorzeichen

| Größe | Konvention |
|---|---|
| Länge, Position, Wellenlänge | nm (Anzeige und Konfiguration) |
| Winkel | Grad |
| Bibliothek | eine Längeneinheit L = `Model.unit_nm` (Bezugslänge des ersten Körpers: Kugelradius, halbe Würfelkante), ω = k₀ = 2πL/λ, ε₀ = μ₀ = 1 |
| Zeitkonvention | e^{−iωt}: Absorption bedeutet Im ε > 0, ε = (n + ik)² mit k ≥ 0 |
| Chiralität | Pasteur-Parameter χ: D = εE + iχH, B = μH − iχE; Helizitätswellen k₊ = ω(n − χ), k₋ = ω(n + χ) (gegen `Medium.k` geprüft) |
| Querschnitte | σ in nm²; Q = σ/(πR²) nur für Kugeln |
| Kräfte | Bibliothek: F = σ_pr · ½ε|E₀|² (|E₀|² = |p|²); GUI: F[pN] = σ_pr · n · I / c mit Intensität I im Außenmedium |
| Feldverstärkung, Chiralität | |E|²/|E₀|² bzw. C/C₀ mit |E₀|² = C₀ = |p|² = `reference_E2` (linear 1, zirkular 2) |
| Polarisation | linear: p = cos ψ·u + sin ψ·v mit (u, v) = `polarization_basis(d)`; zirkular: `circular_polarization(d, ±1)` |

`polarization_basis`: v = d×ẑ normiert (d ∥ ẑ: v = d×x̂), u = v×d. Bei d = +z ist u = x̂ (ψ = 0° ist x-polarisiert). Test
`test_polarization_basis_matches_library` hält die numpy-Kopie der GUI gleich der Bibliothek.

## Konfiguration (`config.py`)

Ein Dictionary mit `schema_version`; Werte in Anzeigeeinheiten.

```json
{ "schema_version": 1, "name": "…",
  "host": {"n": 1.33, "chi": 0.0},
  "bodies": [{"id": "…", "label": "…", "geometry": {"type": "sphere", "params": {…}}, "position": [0,0,0],
              "material": {"type": "tabulated", "params": {…}}, "chi": 0.0}],
  "formulation": {"type": "flat", "params": {}},
  "excitation": {"type": "plane_wave", "params": {…}},
  "observables": [{"type": "extinction", "params": {}}],
  "solver": {"tol": 1e-6, "max_iter": 1000, "threads": 0},
  "resolved": {…}  // nur in Läufen: Bibliotheksfähigkeiten, GUI-Version }
```

Neues Feld: `SCHEMA_VERSION` in `cbgui/__init__.py` erhöhen und in `config.migrate` einen Block ergänzen, der alte Dateien hebt.
Unbekannte Parameter eines Plugins verwirft `Schema.fill`; fehlende werden mit Standardwerten ergänzt.

## Oberfläche

- Das Arbeitsmodell liegt in `st.session_state["cfg"]`. Seiten schreiben direkt hinein; Ersatz des ganzen Modells nur über
  `state.set_cfg` (erhöht den Zähler `gen`, der in allen Widget-Schlüsseln steckt).
- Widget-Schlüssel: `state.wkey(<teile>)`, bei Plugin-Formularen mit `…:<plugin-id>` im Präfix (sonst erbt ein neuer Typ den Zustand
  des alten).
- Meldungen an Benutzer: Deutsch, mit Zahl und Einheit, mit Handlungsaufforderung („Netz verfeinern“).
- Plotly-Abbildungen: Vorlage `plotly_white`, Farben aus `observables.PALETTE`, Achsen mit Einheit.
- Prüfungen: `Issue(level, msg, where)`; `error` sperrt den Start, `warning` informiert, `info` nur Kosten und Hinweise.

## Code

Python ≥ 3.10, `ruff` (Zeilenlänge 140), Typangaben wo sie helfen. Kommentare deutsch und knapp, nur das Warum.
