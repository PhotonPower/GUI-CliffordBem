# ADR 0004 – Versionierte JSON-Konfiguration und in sich geschlossene Run-Verzeichnisse

Status: angenommen (2026-10-16)

## Entscheidung
Das Arbeitsmodell ist ein JSON-fähiges Dictionary mit `schema_version` (`config.migrate` hebt ältere Dateien). Ein Lauf kopiert es mit
den verwendeten Bibliotheksfähigkeiten (`resolved`) in ein eigenes Verzeichnis zusammen mit Status, Ergebnissen, Kennzahlen und Bericht.
Werte bleiben in Anzeigeeinheiten (nm, °); die Umrechnung in die Längeneinheit der Bibliothek geschieht im Worker.

## Folgen
+ jeder Lauf ist reproduzierbar und als Vorlage ladbar; GUI und Worker dürfen verschiedene Versionen sein, solange das Schema verstanden wird
+ `summary.json` liefert Messdaten zur Kalibrierung des Kostenmodells
− Ergebnisdateien sind groß und gehören nicht ins Repository (`.gitignore`); Archivieren ist Sache der Nutzenden
