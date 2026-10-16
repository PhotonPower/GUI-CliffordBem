"""Aufgelöstes Modell: die Konfiguration (``config.py``) mit Plugin-Klassen und vollständigen Parametern.

GUI, Prüfungen, Kostenabschätzung und Worker arbeiten auf demselben ``Model``; so gibt es nur eine Stelle, die
Plugin-Ids, Standardwerte und die Längeneinheit der Bibliothek festlegt.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .base import Excitation, Formulation, Geometry, Material, Observable
from .registry import EXCITATIONS, FORMULATIONS, GEOMETRIES, MATERIALS, OBSERVABLES, load_plugins


@dataclass
class BodyModel:
    index: int
    id: str
    label: str
    geometry: Geometry  # Instanz
    gp: dict
    position: np.ndarray  # nm
    material: Material
    mp: dict
    chi: float

    @property
    def reference_length(self) -> float:
        return float(self.geometry.reference_length(self.gp))


@dataclass
class Model:
    cfg: dict
    name: str
    host_n: float
    host_chi: float
    bodies: list[BodyModel]
    formulation: Formulation
    fp: dict
    excitation: Excitation
    ep: dict
    observables: list[tuple[Observable, dict]]
    solver: dict
    unit_nm: float = 1.0
    extra: dict = field(default_factory=dict)

    @property
    def curved(self) -> bool:
        return self.formulation.element == "curved"

    def n_elements(self) -> int:
        return int(sum(b.geometry.n_elements(b.gp) for b in self.bodies))

    def unknowns(self) -> int:
        return self.n_elements() * self.formulation.unknowns_per_element

    def wavelengths(self) -> list[float]:
        """Alle Wellenlängen, bei denen gerechnet wird (Anregung und Auswertungen)."""
        lams: list[float] = []
        w = self.excitation.wavelength(self.ep)
        if w is not None:
            lams.append(float(w))
        for ob, op in self.observables:
            lams += [float(x) for x in ob.wavelengths(op, self)]
        return lams


def resolve(cfg: dict) -> Model:
    """Konfiguration → Modell. Wirft ``KeyError`` bei unbekannten Plugin-Ids (die Prüfungen fangen das ab)."""
    load_plugins()
    bodies = []
    for i, b in enumerate(cfg["bodies"]):
        g = GEOMETRIES.get(b["geometry"]["type"])
        m = MATERIALS.get(b["material"]["type"])
        gp = g.schema().fill(b["geometry"].get("params"))
        if "_info" in b["geometry"].get("params", {}):  # Ergebnis der Dateiprüfung (Gmsh) durchreichen
            gp["_info"] = b["geometry"]["params"]["_info"]
        bodies.append(BodyModel(
            index=i, id=b.get("id", f"b{i}"), label=b.get("label", f"Körper {i + 1}"), geometry=g(), gp=gp,
            position=np.array(b.get("position", [0, 0, 0]), float), material=m(), mp=m.schema().fill(b["material"].get("params")),
            chi=float(b.get("chi", 0.0))))
    f = FORMULATIONS.get(cfg["formulation"]["type"])
    e = EXCITATIONS.get(cfg["excitation"]["type"])
    obs = []
    for o in cfg.get("observables", []):
        oc = OBSERVABLES.get(o["type"])
        obs.append((oc(), oc.schema().fill(o.get("params"))))
    model = Model(
        cfg=cfg, name=cfg.get("name", "rechnung"), host_n=float(cfg["host"]["n"]), host_chi=float(cfg["host"].get("chi", 0.0)),
        bodies=bodies, formulation=f(), fp=f.schema().fill(cfg["formulation"].get("params")), excitation=e(),
        ep=e.schema().fill(cfg["excitation"].get("params")), observables=obs, solver=dict(cfg.get("solver", {})))
    model.unit_nm = bodies[0].reference_length if bodies else 1.0
    return model
