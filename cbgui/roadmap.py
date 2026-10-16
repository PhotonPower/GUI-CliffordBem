"""Fahrplan: welche Fähigkeit der Bibliothek in der GUI wie umgesetzt ist (Anzeige auf der Hilfeseite).

``feature`` ist der Schlüssel aus ``worker.FEATURE_PROBES`` (Bibliothek hat es) und ``status`` der GUI-Stand:
``done`` umgesetzt, ``next`` als Nächstes, ``planned`` geplant, ``library`` fehlt noch in der Bibliothek (Ausbauplan
in ``docs/ARCHITECTURE.md`` des Bibliotheksprojekts). Die ausführliche Fassung steht in ``docs/07_roadmap.md``.
"""

from __future__ import annotations

ROADMAP: list[dict] = [
    {"area": "Körper", "item": "Kugel, Würfel (gradiert), Gmsh-Datei, mehrere Körper, Dimer-Assistent", "feature": "gmsh", "status": "done",
     "slot": "GEOMETRIES"},
    {"area": "Körper", "item": "Chirale Körper und chirales Außenmedium", "feature": "near_field", "status": "done", "slot": "Körper.chi, host.chi"},
    {"area": "Material", "item": "Au, Ag (Johnson–Christy), n+ik, ε, Drude, YAML-Datei", "feature": "near_field", "status": "done", "slot": "MATERIALS"},
    {"area": "Formulierung", "item": "Konstante Dichten, ebene Dreiecke", "feature": "near_field", "status": "done", "slot": "FORMULATIONS"},
    {"area": "Formulierung", "item": "Gekrümmte Elemente (lineare Dichten, O(h⁴))", "feature": "curved", "status": "done", "slot": "FORMULATIONS"},
    {"area": "Anregung", "item": "Ebene Welle: linear, zirkular, beliebige Richtung", "feature": "near_field", "status": "done", "slot": "EXCITATIONS"},
    {"area": "Auswertung", "item": "Extinktion, Spektrum mit Orientierungsmittelung und CD", "feature": "near_field", "status": "done", "slot": "OBSERVABLES"},
    {"area": "Auswertung", "item": "Nahfeldkarte (Verstärkung, optische Chiralität)", "feature": "near_field", "status": "done", "slot": "OBSERVABLES"},
    {"area": "Auswertung", "item": "Optische Kräfte je Körper", "feature": "forces", "status": "done", "slot": "OBSERVABLES"},
    {"area": "Körper", "item": "Beschichtete Körper: Kern-Schale, Mehrfachschichten (exakt)", "feature": "layered", "status": "next",
     "slot": "FORMULATIONS + Körper.coating"},
    {"area": "Körper", "item": "Dünne Schichten: Dünnschicht-Näherung und Zweitor", "feature": "thin_layer", "status": "next", "slot": "FORMULATIONS"},
    {"area": "Körper", "item": "Beschichtete Körper auf gekrümmten Elementen", "feature": "curved_layered", "status": "next", "slot": "FORMULATIONS"},
    {"area": "Anregung", "item": "Dipol (Emitter): Zerfallsraten, Fluoreszenzverstärkung", "feature": "dipole", "status": "next",
     "slot": "EXCITATIONS + OBSERVABLES"},
    {"area": "Anregung", "item": "Gauß-, fokussierte und Bessel-/Wirbelstrahlen", "feature": "beams", "status": "planned", "slot": "EXCITATIONS"},
    {"area": "Anregung", "item": "Eigene einfallende Felder (Python-Klassen)", "feature": "custom_fields", "status": "planned", "slot": "EXCITATIONS"},
    {"area": "Auswertung", "item": "Streu- und Absorptionsquerschnitt, Fernfeldmuster", "feature": "near_field", "status": "planned", "slot": "OBSERVABLES"},
    {"area": "Auswertung", "item": "Kraftkarten, Kraft auf Emitter, Dipolkraft", "feature": "forces", "status": "planned", "slot": "OBSERVABLES"},
    {"area": "Formulierung", "item": "Lineare Dichten auf ebenen Dreiecken", "feature": "linear", "status": "planned", "slot": "FORMULATIONS"},
    {"area": "Löser", "item": "Krylov-Recycling und HODLR-Vorkonditionierung wählbar", "feature": "recycling", "status": "planned", "slot": "Lauf.solver"},
    {"area": "Betrieb", "item": "Rechnen auf einem Server (Fernstart, Warteschlange)", "feature": "", "status": "planned", "slot": "bridge.start_run"},
    {"area": "Bibliothek", "item": "Substrate (geschichtete Außenmedien)", "feature": "", "status": "library", "slot": "neue Formulierung"},
    {"area": "Bibliothek", "item": "Streumatrix (T-Matrix)", "feature": "", "status": "library", "slot": "neue Auswertung"},
    {"area": "Bibliothek", "item": "Drude-Lorentz-Fits, Größenkorrektur der Dämpfung", "feature": "", "status": "library", "slot": "MATERIALS"},
    {"area": "Bibliothek", "item": "Dipolquellen im chiralen Medium und in Schichten", "feature": "", "status": "library", "slot": "EXCITATIONS"},
]

STATUS_TEXT = {"done": "✅ umgesetzt", "next": "🟡 als Nächstes", "planned": "🔜 geplant", "library": "⏳ wartet auf die Bibliothek"}
