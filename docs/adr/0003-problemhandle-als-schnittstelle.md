# ADR 0003 – `ProblemHandle` trennt Formulierung von Auswertung

Status: angenommen (2026-10-16)

## Kontext
Flache und gekrümmte Elemente haben verschiedene Klassen und Funktionen für Lösen, Nahfeld und Kräfte (`exterior_near_field` gegen
`exterior_near_field_curved`, Auswerter flach gegen gekrümmt). Beschichtete und dünne Schichten kommen mit weiteren Varianten.

## Entscheidung
Eine Formulierung liefert ein `ProblemHandle` je Wellenlänge (`solve`, `near_field`, `force_on_body`, `force_far_field`,
`body_surfaces`). Auswertungen kennen nur das Handle. `Session` hält Netze, baut Handles je Wellenlänge, cached Lösungen je Problem
und teilt sie zwischen Auswertungen.

## Folgen
+ eine neue Formulierung macht alle bestehenden Auswertungen nutzbar; eine neue Auswertung läuft für alle Formulierungen
+ Unterschiede der Bibliothek (z. B. keine Fernfeld-Impulsbilanz bei gekrümmten Elementen) werden an einer Stelle behandelt (`None`)
− kleinster gemeinsamer Nenner: Fähigkeiten, die nur eine Formulierung hat, brauchen eine optionale Methode mit Rückgabe `None`
