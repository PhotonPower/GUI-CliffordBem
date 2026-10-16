"""Formulierungen = Diskretisierung + Problemklasse der Bibliothek.

``flat``   : stückweise konstante Dichten auf ebenen Dreiecken (``ScatteringProblem``), der Standard für alle Formen.
``curved`` : unstetig lineare Dichten auf quadratischen Elementen (``CurvedScatteringProblem``), für Kugeln und
             Gmsh-Netze zweiter Ordnung sehr genau (Konvergenz etwa O(h⁴)).

Weitere Formulierungen (beschichtete Körper: ``LayeredScatteringProblem``, ``ThinLayerScatteringProblem``,
``TwoPortLayerProblem``, ``CurvedLayeredScatteringProblem``; lineare ebene Dichten: ``LinearScatteringProblem``)
kommen als weitere Klassen mit eigenem ``ProblemHandle`` hinzu (docs/07_roadmap.md).
"""

from __future__ import annotations

import time

import numpy as np

from ..base import Formulation, Geometry, Incident, Issue, ProblemHandle, Solution
from ..params import Field
from ..registry import FORMULATIONS

_HM_EPS = Field("hmatrix_eps", "Toleranz der H-Matrix-Kompression", "float", 0.0, "", min=0.0, max=1e-1,
                format="%.1e", advanced=True,
                help="0 = Voreinstellung der Bibliothek (eben 1e-4, gekrümmt 1e-6). Kleiner = genauer, mehr Speicher.")


class _Handle(ProblemHandle):
    """Gemeinsame Umsetzung für ebene und gekrümmte Elemente; die Unterschiede stecken in ``_curved``-Verzweigungen."""

    def __init__(self, cb, session, lam_nm: float, curved: bool, hm_eps: float):
        self.cb, self.s, self.lam, self.curved = cb, session, float(lam_nm), curved
        self.omega = cb.omega_from_wavelength(self.lam, session.unit_nm)
        self.outer = session.outer(self.lam)
        media = session.media(self.lam)
        t0 = time.perf_counter()
        kw = {}
        if hm_eps > 0:
            kw["hmatrix"] = cb.HMatrixParams(eps=hm_eps, eta=2.0) if curved else cb.HMatrixParams(eps=hm_eps)
        cls = cb.CurvedScatteringProblem if curved else cb.ScatteringProblem
        self.P = cls(session.meshes, media, self.omega, outer=self.outer, **kw)
        self.build_seconds = time.perf_counter() - t0
        self.unknowns = int(self.P.unknowns)
        self.hmatrix_bytes = int(self.P.hmatrix_bytes)

    # -- Lösen ---------------------------------------------------------------------------------------------------------
    def solve(self, incident: Incident, tol: float, max_iter: int) -> Solution:
        if incident.kind != "plane_wave":
            raise NotImplementedError("Diese Formulierung löst bisher nur ebene Wellen (Roadmap: Quellen und Strahlen).")
        so = self.cb.SolveOptions(tol=tol, max_iter=max_iter)
        r = self.P.solve_plane_wave(incident.d, incident.p, so)
        return Solution(sigma_ext=float(r.sigma_ext), forward=complex(r.forward), iterations=int(r.iterations),
                        residual=float(r.residual), h=np.asarray(r.h), incident=incident,
                        extra={"converged": bool(r.residual <= 10 * tol)})

    # -- Nahfeld und Kräfte --------------------------------------------------------------------------------------------
    def near_field(self, sol: Solution, points: np.ndarray) -> dict:
        cb, i = self.cb, sol.incident
        fn = cb.exterior_near_field_curved if self.curved else cb.exterior_near_field
        return fn(self.P.mesh, sol.h, self.outer, self.omega, i.d, i.p, np.ascontiguousarray(points, float))

    def _evaluator(self, sol: Solution):
        ev = sol.extra.get("_ev")
        if ev is None:
            cb, i = self.cb, sol.incident
            if self.curved:
                inc = cb.PlaneWaveField(self.outer, self.omega, i.d, i.p)
                b = cb.project_incident_curved(self.P.mesh, inc, self.outer)
                ev = cb.near_field_evaluator_curved(self.P.mesh, sol.h, b, self.outer, self.omega, inc)
            else:
                ev = cb.plane_wave_evaluator(self.P.mesh, sol.h, self.outer, self.omega, i.d, i.p)
            sol.extra["_ev"] = ev
        return ev

    def force_on_body(self, sol: Solution, body: int, delta: float) -> np.ndarray:
        ev = self._evaluator(sol)
        return np.asarray(self.cb.force_on_offset(ev, self.outer, self.s.flat_meshes[body], delta), float)

    def force_far_field(self, sol: Solution) -> np.ndarray | None:
        if self.curved:  # die Impulsbilanz im Fernfeld gibt es bisher nur für ebene Elemente
            return None
        i = sol.incident
        return np.asarray(self.cb.force_from_far_field(self.P.mesh, sol.h, self.outer, self.omega, i.d, i.p,
                                                        sol.sigma_ext), float)

    def body_surfaces(self) -> list:
        return self.s.flat_meshes


@FORMULATIONS.register
class FlatConstant(Formulation):
    id = "flat"
    label = "Standard: konstante Dichten, ebene Dreiecke"
    description = ("Stückweise konstante Dichten auf ebenen Dreiecken (O(h²)). Robust für alle Formen, auch scharfe "
                   "Kanten. Kugel mit 1 280 Dreiecken: etwa 1 % Fehler gegen Mie.")
    element = "flat"
    unknowns_per_element = 8
    cost_reference = {"memory_mb": 58.0, "build_s": 7.5, "iter_s": 0.058, "iterations": 40}
    cost_exponent = 1.25
    fields = (_HM_EPS,)

    def make_handle(self, cb, session, lam_nm):
        return _Handle(cb, session, lam_nm, curved=False, hm_eps=float(session.model.fp.get("hmatrix_eps", 0.0)))


@FORMULATIONS.register
class Curved(Formulation):
    id = "curved"
    label = "Hohe Genauigkeit: lineare Dichten, gekrümmte Elemente"
    description = ("Unstetig lineare Dichten auf quadratischen Elementen (O(h⁴)). Kugel mit 320 Elementen: 0,01 % "
                   "Fehler gegen Mie. Braucht mehr Speicher und Zeit je Element; nur Kugel und Gmsh zweiter Ordnung.")
    element = "curved"
    unknowns_per_element = 24
    cost_reference = {"memory_mb": 477.0, "build_s": 30.0, "iter_s": 0.49, "iterations": 45}
    cost_exponent = 1.2
    requires = ("curved",)
    min_version = "0.47"
    fields = (_HM_EPS,)

    def supports(self, geometry: Geometry, gp: dict) -> list[Issue]:
        ok = geometry.can_curve(gp) if hasattr(geometry, "can_curve") else geometry.supports_curved
        if not ok:
            why = ("hat keine gekrümmte Variante" if not geometry.supports_curved
                   else "braucht eine Gmsh-Datei zweiter Ordnung (ElementOrder 2)")
            return [Issue("error", f"„{geometry.label}“ {why}; bitte die Formulierung „Standard“ wählen.", "Formulierung")]
        return []

    def make_handle(self, cb, session, lam_nm):
        return _Handle(cb, session, lam_nm, curved=True, hm_eps=float(session.model.fp.get("hmatrix_eps", 0.0)))
