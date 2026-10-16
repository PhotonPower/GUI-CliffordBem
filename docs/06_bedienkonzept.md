# 06 Bedienkonzept

Zielgruppe: Forschende der Nano-Optik, die die Physik kennen, aber nicht jeden Parameter der Bibliothek. Leitgedanken: sinnvolle
Voreinstellungen, Fehler **vor** dem Rechnen finden, Kosten sichtbar machen, jedes Ergebnis reproduzierbar.

## Ablauf

```
Start ─► 1 Modell ─► 2 Anregung ─► 3 Auswertung ─► 4 Berechnung ─► 5 Ergebnisse        Läufe · Bibliothek und Fahrplan
 Vorlage   Körper      λ, Richtung    Kästchen        Prüfung,         Abbildungen,       Archiv, Vergleich, Fähigkeiten,
 oder neu  Material    Polarisation   je Größe        Kosten, Start,   Export,            Plugins, Fahrplan
           Umgebung    Vorschau       + Parameter     Fortschritt      „als Vorlage“
           Netz
```

Seitenleiste (immer): Name des Modells, Bibliotheksstand, Körper/Unbekannte/Speicher/Zeit, Ampel der Prüfung, Konfiguration
speichern und laden.

## Seiten

| Seite | Inhalt | Besonderheiten |
|---|---|---|
| Start | Überblick, fünf Schritte, **Vorlagen**, letzte Läufe | Vorlage laden führt direkt zum Modell |
| 1 Modell | Reiter *Körper* (je Körper ein Block: Name, Form, Größe, Netzfeinheit, Lage, Material mit Schnellauswahl, χ; Duplizieren, Entfernen, Dimer-Assistent), *Umgebung* (Schnellknöpfe Luft/Wasser/Glas, n, χ), *Netz und Genauigkeit* (Formulierung, Entwurf/Standard/Fein) | rechts 3D-Vorschau, Elemente, Unbekannte, Speicher, Zeit; Prüfungen als Expander |
| 2 Anregung | λ, Richtung (Voreinstellungen oder θ, φ), Polarisation (linear mit ψ, zirkular) | Pfeile k (rot) und E (blau) in der Vorschau; Tabelle ε und n+ik der Materialien bei λ |
| 3 Auswertung | Kästchen je Auswertung mit Beschreibung; Parameter nur bei aktivem Kästchen | Gesamtkosten; nicht verfügbare Auswertungen ausgegraut mit Grund |
| 4 Berechnung | Zusammenfassung, Prüfliste (Fehler rot, Warnungen gelb, Hinweise blau), Kosten, Start | Start gesperrt bei Fehlern oder fehlender Bibliothek; Fortschritt aktualisiert sich alle 2 s; Abbrechen |
| 5 Ergebnisse | Lauf wählen; je Auswertung Reiter mit Kennzahlen, Einzelheiten, Abbildungen, CSV | Ansichtsoptionen (Log-Skala, Größe, Umrisse); Rohdaten, Konfiguration, Bericht laden; „als Vorlage übernehmen“ |
| Läufe | Archiv mit Zustand, Dauer, Unbekannten; Löschen mit Bestätigung; **Spektren mehrerer Läufe überlagern** | Parameterstudien: Läufe unter eigenem Namen starten, hier vergleichen |
| Bibliothek und Fahrplan | Version, Kerne, Speicher, Fähigkeiten, Plugins, Fahrplan | Anleitung, wenn keine Bibliothek erreichbar ist |

## Gestaltungsregeln

1. **Fehler vor dem Rechnen.** Jede bekannte Falle aus der Bibliotheksdoku wird zur Prüfregel (`checks.py`) mit Zahlen und
   Handlungsaufforderung.
2. **Kosten zuerst.** Elemente, Unbekannte, Speicher und Zeit stehen beim Modell, in der Seitenleiste und vor dem Start.
3. **Sichere Voreinstellungen.** Standardformulierung ist die robuste (eben); „Hohe Genauigkeit“ bleibt eine bewusste Wahl.
4. **Referenz sichtbar.** Bei Einzelkugeln zeigt jede Extinktion die Abweichung zu Mie.
5. **Reproduzierbar.** Jeder Lauf speichert Konfiguration, Bibliotheksstand und Bericht; „als Vorlage übernehmen“ führt zurück.
6. **Ehrlich bei Unsicherheit.** Nicht konvergierte Lösungen werden gemeldet, Schätzungen als Schätzung bezeichnet.
7. **Erweitern ohne Seitenumbau.** Formulare, Prüfungen, Kosten und Ergebnisseiten entstehen aus den Plugin-Deklarationen.

## Geplante Bedienverbesserungen

Siehe `backlog.md`: Parameterstudien (Serienläufe über einen Wert), Fortschrittsanzeige je Iteration, Querschnittsansicht
des Netzes, Speichern von Ansichten als Bild.
