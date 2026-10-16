# Mitarbeit

Sprache des Projekts: **Deutsch** (Oberfläche, Dokumentation, Kommentare), Bezeichner im Code englisch.

## Ablauf

1. Zweig anlegen, Änderung klein halten (eine Fähigkeit pro Pull Request).
2. `ruff check .` und `pytest -m "not library"` müssen grün sein; bei Änderungen an Worker, Formulierungen oder Auswertungen
   zusätzlich `pytest` mit gebauter Bibliothek (`docs/04_tests.md`).
3. `CHANGELOG.md` ergänzen; neue Bibliotheksaufrufe in `docs/05_bibliotheksschnittstelle.md` mit der geprüften Version eintragen.
4. Bei einer Architekturentscheidung eine Notiz in `docs/adr/` anlegen.

## Neue Fähigkeit der Bibliothek einbauen

Lies [`docs/02_plugin_leitfaden.md`](docs/02_plugin_leitfaden.md): meist ist es **eine Klasse** in `cbgui/plugins/`, ein Eintrag in
`worker.FEATURE_PROBES`, ein Eintrag in `cbgui/roadmap.py` und ein Test.

## Regeln

- Plugin-Module importieren beim Laden nur Standardbibliothek und numpy (ADR 0001); `cliffordbem` kommt als Argument `cb`.
- Alle Längen in nm, Winkel in Grad (`docs/03_konventionen.md`).
- Keine Zugangsdaten ins Repository (`.gitignore` schließt Tokendateien aus).
