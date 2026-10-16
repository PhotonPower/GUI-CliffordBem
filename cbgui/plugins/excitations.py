"""Eingebaute Anregungen. Aktuell: ebene Welle (linear oder zirkular).

Erweiterungspunkt (docs/07_roadmap.md): Dipol (``cb.DipoleField``), Gauß- und fokussierte Strahlen
(``cb.BeamField``), eigene Felder (``cb.CustomField``) = jeweils eine Klasse mit ``kind = "source"`` und
``Incident(kind="field", field=...)``.
"""

from __future__ import annotations

import math

import numpy as np

from ..base import Excitation, Incident, Issue
from ..params import Field
from ..registry import EXCITATIONS

DIRECTIONS = {
    "z": ("+z (entlang der Achse, Standard)", 0.0, 0.0),
    "-z": ("−z", 180.0, 0.0),
    "x": ("+x", 90.0, 0.0),
    "y": ("+y", 90.0, 90.0),
    "custom": ("frei (θ, φ)", None, None),
}


def direction_vector(theta_deg: float, phi_deg: float) -> np.ndarray:
    t, f = math.radians(theta_deg), math.radians(phi_deg)
    return np.array([math.sin(t) * math.cos(f), math.sin(t) * math.sin(f), math.cos(t)])


def polarization_basis(d) -> tuple[np.ndarray, np.ndarray]:
    """Wie ``cb.polarization_basis`` (gegen die Bibliothek getestet): v = d×ẑ normiert (d ∥ ẑ: v = d×x̂), u = v×d."""
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    v = np.cross(d, [0.0, 0.0, 1.0])
    if np.linalg.norm(v) < 1e-9:
        v = np.cross(d, [1.0, 0.0, 0.0])
    v /= np.linalg.norm(v)
    return np.cross(v, d), v


@EXCITATIONS.register
class PlaneWave(Excitation):
    id = "plane_wave"
    label = "Ebene Welle"
    description = "Ebene Welle mit Einfallsrichtung und linearer oder zirkularer Polarisation."
    kind = "plane_wave"
    fields = (
        Field("wavelength", "Vakuumwellenlänge λ", "float", 530.0, "nm", min=100.0, max=20000.0, step=10.0,
              help="Für Auswertungen bei einer Wellenlänge. Das Spektrum hat einen eigenen Bereich."),
        Field("direction", "Ausbreitungsrichtung", "choice", "z", choices=tuple((k, v[0]) for k, v in DIRECTIONS.items())),
        Field("theta", "Polarwinkel θ (von +z)", "float", 0.0, "°", min=0.0, max=180.0, step=1.0,
              visible_if=lambda v: v.get("direction") == "custom"),
        Field("phi", "Azimut φ (von +x)", "float", 0.0, "°", min=-360.0, max=360.0, step=1.0,
              visible_if=lambda v: v.get("direction") == "custom"),
        Field("polarization", "Polarisation", "choice", "linear",
              choices=(("linear", "linear"), ("circ_plus", "zirkular σ₊ (links, positive Helizität)"),
                       ("circ_minus", "zirkular σ₋ (rechts, negative Helizität)"))),
        Field("psi", "Polarisationswinkel ψ", "float", 0.0, "°", min=-180.0, max=180.0, step=5.0,
              visible_if=lambda v: v.get("polarization") == "linear",
              help="0° = Richtung u der Bibliothek (bei Einfall entlang z: x-Achse), 90° = v (y-Achse). "
                   "Die Vorschau zeigt den Pfeil."),
    )

    def _angles(self, p):
        if p["direction"] == "custom":
            return p["theta"], p["phi"]
        _, t, f = DIRECTIONS[p["direction"]]
        return t, f

    def wavelength(self, p):
        return p["wavelength"]

    def direction(self, p):
        return direction_vector(*self._angles(p))

    def is_circular(self, p):
        return p["polarization"] != "linear"

    def polarization_vector(self, p) -> np.ndarray | None:
        """Reeller E-Vektor für die Vorschau (linear); None bei zirkularer Polarisation."""
        if self.is_circular(p):
            return None
        u, v = polarization_basis(self.direction(p))
        psi = math.radians(p["psi"])
        return math.cos(psi) * u + math.sin(psi) * v

    def describe(self, p):
        pol = {"linear": f"linear (ψ = {p['psi']:g}°)", "circ_plus": "zirkular σ₊", "circ_minus": "zirkular σ₋"}[p["polarization"]]
        d = self.direction(p)
        return f"λ = {p['wavelength']:g} nm, Richtung ({d[0]:+.2f}, {d[1]:+.2f}, {d[2]:+.2f}), {pol}"

    def validate(self, p, model):
        out = []
        if model is not None and abs(model.host_chi) > 0 and not self.is_circular(p):
            out.append(Issue("error", "Im chiralen Außenmedium ist nur zirkulare Polarisation möglich "
                                      "(Helizitätswellen, docs/python.md).", "Anregung"))
        return out

    def build(self, cb, p, outer):
        t, f = self._angles(p)
        d = tuple(float(x) for x in direction_vector(t, f))
        if p["polarization"] == "linear":
            u, v = cb.polarization_basis(d)
            psi = math.radians(p["psi"])
            pol = tuple(complex(x) for x in (math.cos(psi) * np.asarray(u) + math.sin(psi) * np.asarray(v)))
        else:
            s = +1 if p["polarization"] == "circ_plus" else -1
            pol = tuple(complex(x) for x in cb.circular_polarization(d, s))
        return Incident(kind="plane_wave", d=d, p=pol, label=self.describe(p))
