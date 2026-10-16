# ADR 0005 – Vorab-Prüfungen und Kostenabschätzung als eigene Schicht

Status: angenommen (2026-10-16)

## Kontext
Die Bibliotheksdokumentation nennt viele Fallen (Resonanzfenster, Netz gegenüber Wellenlänge, Spalt kleiner als Elementkante, chirales
Medium nur zirkular, Speicherbedarf). Wer sie erst nach Stunden Rechenzeit entdeckt, verliert Zeit.

## Entscheidung
`checks.collect_issues` bewertet ein aufgelöstes Modell (`Issue` mit Stufe `error`, `warning`, `info`) und läuft in der GUI bei jeder
Änderung und noch einmal im Worker. `cost.estimate` skaliert Messwerte der Bibliothek je Formulierung. Fehler sperren den Start.
Materialwerte für Prüfungen kommen ohne Bibliothek aus `Material.eps_numpy`, sonst über den Worker (zwischengespeichert).

## Folgen
+ Fallen werden zu Regeln mit Zahlen und Handlungsaufforderung; Tests je Regel
+ Schätzungen sind sichtbar als Schätzung (Faktor 2) und kalibrierbar
− Regeln müssen mit der Bibliothek nachgeführt werden (Verweise auf deren Dokumente stehen in den Meldungen)
