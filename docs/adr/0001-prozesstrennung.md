# ADR 0001 – GUI und Rechnung in getrennten Prozessen, gekoppelt über Dateien

Status: angenommen (2026-10-16)

## Kontext
Die Bibliothek wird je nach Rechner in eigener Umgebung gebaut (z. B. MSYS2 UCRT64, dort ohne Streamlit). Rechnungen dauern Minuten bis
Stunden und können den Speicher erschöpfen. Ein Fernstart auf einem großen Rechner ist geplant. Die Schwester-GUIs (SpeckleBEM) haben
dieselbe Entscheidung getroffen.

## Entscheidung
Der GUI-Prozess importiert `cliffordbem` nie. Der Worker (`python -m cbgui.worker`) läuft in einem Interpreter, der über
`CBGUI_WORKER_PYTHON` und `CBGUI_WORKER_PYTHONPATH` gewählt wird. Kurze Abfragen: JSON in der letzten Ausgabezeile. Lange Läufe:
abgekoppelter Prozess, Austausch nur über das Run-Verzeichnis.

## Folgen
+ unabhängige Umgebungen, Absturzisolation, neustartsichere Läufe, gleicher Vertrag für Fernstart, GUI ohne Bibliothek bedienbar
− jede Abfrage kostet einen Prozessstart (Sekunden; zwischengespeichert)
− Plugin-Module müssen in beiden Umgebungen importierbar sein (nur Standardbibliothek und numpy)
− Fortschritt wird gepollt (`status.json`), nicht gepusht
