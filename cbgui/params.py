"""Deklarative Parameterschemas.

Ein Plugin beschreibt seine Eingaben einmal als ``Field``-Objekte. Daraus entstehen die Streamlit-Widgets,
die Bereichsprüfung und die Standardwerte. Alle Längen sind in **nm**, Winkel in **Grad**, Wellenlängen in **nm**
(docs/03_konventionen.md); die Plugins rechnen erst im Worker in die Längeneinheit der Bibliothek um.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

KINDS = ("float", "int", "choice", "bool", "text", "file")


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = "float"  # float | int | choice | bool | text | file
    default: Any = 0.0
    unit: str = ""  # nur Anzeige: "nm", "°", "eV", ...
    min: float | None = None
    max: float | None = None
    step: float | None = None
    choices: tuple = ()  # ((wert, bezeichnung), ...)
    help: str = ""
    advanced: bool = False  # in einem Expander "Erweitert" anzeigen
    visible_if: Callable[[dict], bool] | None = None  # bekommt die Anzeigewerte des ganzen Formulars
    format: str | None = None  # printf-Format für Zahlenfelder, z. B. "%.3f"

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"Field {self.key!r}: unbekannte Art {self.kind!r}")
        if self.kind == "choice" and not self.choices:
            raise ValueError(f"Field {self.key!r}: choice braucht choices")


class Schema:
    def __init__(self, fields=()):
        self.fields = tuple(fields)
        keys = [f.key for f in self.fields]
        if len(keys) != len(set(keys)):
            raise ValueError(f"doppelte Feldschlüssel im Schema: {keys}")

    def defaults(self) -> dict:
        return {f.key: f.default for f in self.fields}

    def fill(self, values: dict | None) -> dict:
        """Standardwerte, überlagert mit den bekannten Schlüsseln von ``values`` (Unbekanntes entfällt)."""
        out = self.defaults()
        out.update({k: v for k, v in (values or {}).items() if k in out})
        return out

    def is_visible(self, f: Field, values: dict) -> bool:
        return f.visible_if is None or bool(f.visible_if(values))

    def errors(self, values: dict) -> list[str]:
        """Bereichsfehler der sichtbaren Felder (deutsche Meldungen für die Oberfläche)."""
        v = self.fill(values)
        out = []
        for f in self.fields:
            if not self.is_visible(f, v):
                continue
            x = v[f.key]
            if f.kind in ("float", "int"):
                if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
                    out.append(f"{f.label}: keine gültige Zahl")
                    continue
                u = f" {f.unit}" if f.unit else ""
                if f.min is not None and x < f.min:
                    out.append(f"{f.label} = {x:g}{u} liegt unter {f.min:g}{u}")
                if f.max is not None and x > f.max:
                    out.append(f"{f.label} = {x:g}{u} liegt über {f.max:g}{u}")
            elif f.kind == "choice" and x not in [c[0] for c in f.choices]:
                out.append(f"{f.label}: unbekannte Auswahl {x!r}")
        return out

    def describe(self) -> list[dict]:
        """Tabellenzeilen für die Dokumentation (docs/02_plugin_leitfaden.md)."""
        return [
            {"key": f.key, "label": f.label, "kind": f.kind, "default": f.default, "unit": f.unit,
             "min": f.min, "max": f.max, "help": f.help}
            for f in self.fields
        ]
