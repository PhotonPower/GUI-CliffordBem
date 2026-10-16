"""Basisklassen der fünf Plugin-Arten und die kleinen Datentypen, die sie austauschen.

Prozessaufteilung (docs/01_konzept.md, ADR 0001):

* GUI-Prozess: ``Geometry.preview``, ``validate``, Größen- und Kostenabschätzung, ``Observable.figures``.
  Hier gibt es **kein** ``cliffordbem``.
* Worker-Prozess: ``Geometry.build``, ``Material.eps``, ``Excitation.build``, ``Formulation.make_handle``,
  ``Observable.compute``. Die Bibliothek wird als Argument ``cb`` übergeben (das Modul ``cliffordbem``).

Alle ``p``-Argumente sind Dictionaries mit Anzeigewerten (nm, Grad, ...), vollständig mit Standardwerten gefüllt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

import numpy as np

from .params import Field
from .registry import Plugin


@dataclass
class Issue:
    level: str  # "error" blockiert den Lauf, "warning" und "info" nicht
    msg: str
    where: str = ""  # z. B. "Körper 2", "Netz", "Auswertung Spektrum"

    def __post_init__(self):
        if self.level not in ("error", "warning", "info"):
            raise ValueError(f"Issue.level: {self.level!r}")


# --------------------------------------------------------------------------------------------------------------------
# Geometrie
# --------------------------------------------------------------------------------------------------------------------
class Geometry(Plugin):
    """Ein Körper (Form + Größe + Netzfeinheit). Position, Material und Chiralität gehören zum Körper, nicht zur Form."""

    #: gekrümmte (quadratische) Elemente verfügbar? Dann liefert ``build(..., curved=True)`` ein QuadraticMesh.
    supports_curved: ClassVar[bool] = False
    #: Kugel: Mie-Referenz möglich (mie_radius)
    is_sphere: ClassVar[bool] = False
    #: Schlüssel des Netzfeinheits-Parameters und Voreinstellungen (Entwurf, Standard, Fein) je Elementart – für die
    #: Schnelleinstellung „Genauigkeit“ der Oberfläche; None = nicht vorhanden (z. B. Gmsh-Datei)
    resolution_key: ClassVar[str | None] = None
    resolution_presets: ClassVar[dict] = {}

    def prepare(self, cb, p: dict) -> dict:
        """Worker, vor Prüfung und Rechnung: Parameter mit Angaben ergänzen, die nur die Bibliothek liefert
        (z. B. Gmsh-Datei einlesen). Gibt die (ggf. erweiterten) Parameter zurück; Standard: unverändert."""
        return p

    def can_curve(self, p: dict) -> bool:
        """Gekrümmte Elemente für diese Parameter möglich? (Gmsh: nur bei Elementen zweiter Ordnung)"""
        return self.supports_curved

    def section(self, p: dict, plane: str, offset: float):
        """Schnitt des Körpers (um den Ursprung) mit der Ebene ``plane`` ("xy", "xz", "yz") im Abstand ``offset`` (nm)
        entlang der Normalen: Liste von (u, v)-Linienzügen für die Umrisse in Nahfeldkarten; leer/None = keine."""
        return None

    def reference_length(self, p: dict) -> float:
        """Bezugslänge in nm (Kugelradius, halbe Würfelkante); Grundlage der Längeneinheit der Bibliothek."""
        raise NotImplementedError

    def bounding_radius(self, p: dict) -> float:
        """Radius (nm) einer Kugel um den Körpermittelpunkt, die den Körper enthält."""
        return self.reference_length(p)

    def has_sharp_edges(self, p: dict) -> bool:
        return False

    def n_elements(self, p: dict) -> int:
        """Anzahl der Dreiecke (flach wie gekrümmt gleich)."""
        raise NotImplementedError

    def element_size(self, p: dict) -> float:
        """Typische Elementkante in nm (für die Prüfung gegen die Wellenlänge)."""
        raise NotImplementedError

    def validate(self, p: dict) -> list[Issue]:
        return []

    def preview(self, p: dict) -> tuple[np.ndarray, np.ndarray]:
        """Leichte Vorschau (Eckpunkte in nm um den Mittelpunkt, Dreiecke) ohne Bibliothek."""
        raise NotImplementedError

    def build(self, cb, p: dict, unit_nm: float, curved: bool = False):
        """Netz im Körperrahmen, **um den Ursprung**, Längen in Einheiten von ``unit_nm`` (Worker).
        Flach: ``cb.TriangleMesh``; gekrümmt: ``cb.QuadraticMesh``. Verschoben wird vom Aufrufer (``cb.translated``)."""
        raise NotImplementedError

    def mie_radius(self, p: dict) -> float | None:
        return self.reference_length(p) if self.is_sphere else None


# --------------------------------------------------------------------------------------------------------------------
# Material
# --------------------------------------------------------------------------------------------------------------------
class Material(Plugin):
    def eps_numpy(self, p: dict, lam_nm: float) -> complex | None:
        """ε(λ) ohne Bibliothek, falls möglich (Vorschau, Prüfungen); sonst None."""
        return None

    def eps(self, cb, p: dict, lam_nm: float) -> complex:
        """ε(λ) im Worker. Zeitkonvention e^{-iωt}: Absorption bedeutet Im ε > 0."""
        raise NotImplementedError

    def lambda_range(self, p: dict, caps: dict | None = None) -> tuple[float, float] | None:
        """Gültigkeitsbereich in nm, falls begrenzt (tabellierte Daten; ``caps`` = Bibliotheksfähigkeiten)."""
        return None

    def validate(self, p: dict) -> list[Issue]:
        return []

    def short(self, p: dict) -> str:
        return self.label


# --------------------------------------------------------------------------------------------------------------------
# Anregung
# --------------------------------------------------------------------------------------------------------------------
@dataclass
class Incident:
    """Was der Worker an die Formulierung übergibt. ``kind='plane_wave'``: Richtung ``d`` und Polarisation ``p``
    (komplexer Einheitsvektor, senkrecht zu d). ``kind='field'``: ein einfallendes Feld der Bibliothek in ``field``
    (Dipol, Strahl, ...; Erweiterungspunkt, siehe docs/07_roadmap.md)."""

    kind: str
    d: tuple[float, float, float] | None = None
    p: tuple[complex, complex, complex] | None = None
    field: Any = None
    label: str = ""


class Excitation(Plugin):
    #: "plane_wave" oder "source" (Quelle im Raum, z. B. Dipol)
    kind: ClassVar[str] = "plane_wave"

    def validate(self, p: dict, model) -> list[Issue]:
        return []

    def describe(self, p: dict) -> str:
        return ""

    def wavelength(self, p: dict) -> float | None:
        """Wellenlänge (nm) für Auswertungen bei einer Wellenlänge; None, wenn die Anregung keine festlegt."""
        return None

    def direction(self, p: dict) -> np.ndarray | None:
        """Einfallsrichtung als Einheitsvektor (für den Pfeil in der Vorschau); None bei Quellen."""
        return None

    def is_circular(self, p: dict) -> bool:
        return False

    def build(self, cb, p: dict, outer) -> Incident:
        """Worker: ``outer`` ist das Außenmedium (cb.Medium)."""
        raise NotImplementedError


# --------------------------------------------------------------------------------------------------------------------
# Formulierung (Diskretisierung + Problemklasse)
# --------------------------------------------------------------------------------------------------------------------
@dataclass
class Solution:
    sigma_ext: float  # Einheiten² der Bibliothek
    forward: complex
    iterations: int
    residual: float
    h: np.ndarray  # Gesamtspur außen
    incident: Incident
    extra: dict = field(default_factory=dict)


class ProblemHandle:
    """Ein gebautes Streuproblem bei fester Wellenlänge (Worker). Die Formulierung entscheidet, welche
    Bibliotheksklassen und -funktionen dahinterstehen; Auswertungen sprechen nur diese Schnittstelle an."""

    unknowns: int = 0
    hmatrix_bytes: int = 0
    build_seconds: float = 0.0

    def solve(self, incident: Incident, tol: float, max_iter: int) -> Solution:
        raise NotImplementedError

    def near_field(self, sol: Solution, points: np.ndarray) -> dict:
        raise NotImplementedError

    def force_on_body(self, sol: Solution, body: int, delta: float) -> np.ndarray:
        raise NotImplementedError

    def force_far_field(self, sol: Solution) -> np.ndarray:
        raise NotImplementedError

    def body_surfaces(self) -> list:
        """Flache Netze je Körper (cb.TriangleMesh) in Bibliothekseinheiten, verschoben."""
        raise NotImplementedError


class Formulation(Plugin):
    #: "flat" (ebene Dreiecke) oder "curved" (quadratische Elemente)
    element: ClassVar[str] = "flat"
    #: Unbekannte je Element (8 konstant, 24 linear/gekrümmt)
    unknowns_per_element: ClassVar[int] = 8
    #: Kostenmodell: Speicher MB bei 1280 Elementen, Aufbau s bei 1280 Elementen (ein Kern), s je Iteration bei 1280
    cost_reference: ClassVar[dict] = {"memory_mb": 58.0, "build_s": 8.0, "iter_s": 0.06, "iterations": 40}
    cost_exponent: ClassVar[float] = 1.25

    def supports(self, geometry: Geometry, gp: dict) -> list[Issue]:
        """Prüft, ob die Formulierung diese Geometrie rechnen kann (``geometry`` ist eine Instanz)."""
        return []

    def make_handle(self, cb, session, lam_nm: float) -> ProblemHandle:
        raise NotImplementedError


# --------------------------------------------------------------------------------------------------------------------
# Auswertung
# --------------------------------------------------------------------------------------------------------------------
class Observable(Plugin):
    """Eine Auswertung: rechnet im Worker (``compute``), zeichnet in der GUI (``figures``).

    ``compute`` bekommt die ``Session`` des Laufs (worker.Session) und gibt ein Dictionary aus NumPy-Arrays,
    Zahlen und Zeichenketten zurück; es wird als ``obs<i>__<schlüssel>`` in ``results.npz`` gespeichert.
    ``figures`` bekommt dieses Dictionary zurück und darf die Bibliothek nicht brauchen."""

    #: Felder der Ergebnisansicht (z. B. logarithmische Skala); Werte kommen als ``view`` in ``figures``
    view_fields: ClassVar[tuple[Field, ...]] = ()

    def validate(self, p: dict, model) -> list[Issue]:
        return []

    def wavelengths(self, p: dict, model) -> list[float]:
        """Wellenlängen (nm), bei denen die Auswertung rechnet (für Prüfungen von Netz und Materialbereich);
        leer = Wellenlänge der Anregung."""
        return []

    def n_builds(self, p: dict, model) -> int:
        """Anzahl der Problemaufbauten (Wellenlängen) – für die Kostenabschätzung."""
        return 1

    def n_solves(self, p: dict, model) -> int:
        """Anzahl der Lösungen (rechte Seiten) insgesamt."""
        return 1

    def compute(self, session, p: dict) -> dict[str, Any]:
        raise NotImplementedError

    def figures(self, data: dict, ctx: dict, view: dict) -> list:
        return []

    def summary(self, data: dict) -> dict[str, str]:
        return {}

    def details(self, data: dict) -> list[tuple[str, str]]:
        """Weitere Kennzahlen als (Name, Wert)-Liste für eine Tabelle unter den Kennzahlen."""
        return []

    def csv(self, data: dict) -> str | None:
        """Tabelle als CSV-Text für den Export, falls sinnvoll."""
        return None
