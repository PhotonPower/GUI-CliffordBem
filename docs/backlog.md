# Backlog

Priorität: A nächster Schritt, B danach, C Idee.

## GUI

| P | Aufgabe |
|---|---|
| A | Beschichtete Körper (Kern-Schale) als Formulierung `layered`/`curved_layered` (Roadmap) |
| A | Dipol-Anregung und Auswertung Zerfallsraten/Fluoreszenz |
| A | Optik der Seiten im Browser durchsehen (bisher nur AppTest), Feinschliff Abstände/Beschriftungen |
| B | Serienläufe (Parameterstudie über Radius, Spalt, χ, …) mit gruppierter Darstellung |
| B | Streu-/Absorptionsquerschnitt (aus Fernfeld) und Fernfeldmuster |
| B | Kostenmodell an Messwerten kalibrieren (Läufe sammeln, `docs/04_tests.md`), Mehrkern-Verhalten messen |
| B | Fortschritt je Lösung (GMRES-Rückruf), sobald die Bibliothek einen anbietet |
| B | Windows/MSYS2 prüfen (`CBGUI_WORKER_PYTHON`), Hinweise in der README ergänzen |
| C | Geometrie „Zylinder/Stäbchen“ und „Ellipsoid“ über Gmsh-Erzeugung im GUI-Prozess (wie GUI-SpeckleBEM) |
| C | Abbildungen als PNG (kaleido) und Notizen je Lauf |
| C | Mehrsprachigkeit (derzeit nur Deutsch) |

## Wünsche an die Bibliothek (nicht hier ändern)

- Fortschrittsrückruf und kooperativer Abbruch in `solve_plane_wave` (derzeit Prozess beenden).
- `curved_hmatrix_params()` in Python exportieren (heute nur über die Voreinstellung des Konstruktors erreichbar).
- Rückgabe der Residuenverläufe und der Zeiten (Aufbau/Lösen) aus den Problemklassen.
- Typ-Stubs (`.pyi`) und Wheels, damit die GUI-Installation ohne Compiler möglich wird.
- Impulsbilanz im Fernfeld und Streuquerschnitt auch für gekrümmte Elemente.
- Mie-Referenz (`tools/mie*.py`) als Paketbestandteil, dann entfällt `cbgui/reference/mie.py` für die achirale Kugel.
