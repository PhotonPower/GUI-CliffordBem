# ADR 0002 – Fünf Plugin-Registries mit deklarativen Parameterschemas

Status: angenommen (2026-10-16)

## Kontext
Die Bibliothek wächst (Beschichtungen, Dipole, Strahlen, Substrate). Feste Formulare würden bei jeder Erweiterung Seitenumbau bedeuten.

## Entscheidung
Geometrie, Material, Anregung, Formulierung und Auswertung sind Registries. Ein Plugin deklariert `Field`s einmal; daraus entstehen
Formular, Bereichsprüfung und Standardwerte. Plugins deklarieren benötigte Bibliotheksfähigkeiten (`requires`, `min_version`); die GUI
blendet nicht Verfügbares mit Grund aus. Entdeckung durch Import von `cbgui/plugins/*` und Entry-Point-Gruppe `cbgui.plugins`.

## Folgen
+ neue Fähigkeit = eine Klasse; Formulare, Prüfungen, Kosten und Ergebnisseite folgen
+ ältere Bibliotheken funktionieren mit weniger Plugins statt gar nicht
− Formulare sind generisch (Raster aus Feldern); Sonderlayouts brauchen eine neue Feldart
− Module müssen leichtgewichtig importierbar bleiben (ADR 0001)
