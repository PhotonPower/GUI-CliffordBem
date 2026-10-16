# Übergabe (Stand GUI 0.1, Bibliothek 0.63)

## Was fertig und geprüft ist

Siehe `CHANGELOG.md` und `docs/04_tests.md` (65 Tests, 14 mit Bibliothek). Wichtige Kontrollen: Kugel gegen Mie (eben O(h²): 4,7 / 1,2 /
0,5 % bei n = 4 / 8 / 12; gekrümmt 0,9 / 0,2 / 0,07 % bei n = 2 / 3 / 4), Gmsh-Kugel zweiter Ordnung 0,18 % gegen Mie (eben 10,6 %),
Kraft = σ·n·I/c mit verschwindenden Querkräften, Impulsbilanz auf 0,2–1 %, Dimer zieht sich an, chiraler Körper CD ≠ 0, achiral ≈ 0,
Absturz- und Abbrucherkennung.

## Was nicht geprüft ist

- Aussehen im Browser (Layout, Plotly-Darstellung): nur AppTest ohne Sichtprüfung.
- Windows/MSYS2 und Streamlit-Versionen außer der aktuellen.
- Große Läufe (> 20 000 Elemente) und die Genauigkeit des Kostenmodells darüber.
- Mehrkern-Skalierung (Tests liefen auf einem Kern).

## Hinweise für die Weiterarbeit

- Beginne mit `CLAUDE.md`, dann `docs/02_plugin_leitfaden.md` und `docs/07_roadmap.md`.
- Bibliothek bauen dauert auf einem Kern etwa 15 Minuten; Testlauf mit Bibliothek eine Minute.
- Die Bibliothek wird von hier aus nicht verändert; Wünsche stehen im Backlog.
- Zugangsdaten gehören nie ins Repository.
