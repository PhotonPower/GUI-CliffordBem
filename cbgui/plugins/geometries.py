"""Eingebaute Geometrien: Kugel, Würfel, Gmsh-Datei.

Konventionen: Längen in nm; die Bibliothek rechnet in einer Einheit ``unit_nm`` (Kugelradius = 1 für die erste Kugel),
``build`` liefert Netze **um den Ursprung** in diesen Einheiten, die Verschiebung setzt die Session.
Modulweite Importe nur Standardbibliothek und numpy (docs/02_plugin_leitfaden.md).
"""

from __future__ import annotations

import math
import os

import numpy as np

from ..base import Geometry, Issue
from ..meshprev import box, icosphere
from ..params import Field
from ..registry import GEOMETRIES

FILE_UNITS_NM = {"nm": 1.0, "µm": 1e3, "mm": 1e6, "m": 1e9}


@GEOMETRIES.register
class Sphere(Geometry):
    id = "sphere"
    label = "Kugel"
    description = "Kugel aus einem unterteilten Ikosaeder (20 n² Dreiecke). Mit gekrümmten Elementen sehr genau."
    supports_curved = True
    is_sphere = True
    resolution_key = "n"
    resolution_presets = {"flat": (4, 8, 16), "curved": (2, 3, 5)}
    fields = (
        Field("radius", "Radius", "float", 20.0, "nm", min=0.5, max=5000.0, step=1.0),
        Field("n", "Netzfeinheit n", "int", 8, "", min=1, max=40, step=1,
              help="Dreiecke = 20 n²: n = 4 → 320, n = 8 → 1 280, n = 16 → 5 120. "
                   "Fehler gegen Mie (Goldkugel): eben n = 8 ≈ 1,2 %, gekrümmt n = 3 ≈ 0,2 %."),
    )

    def reference_length(self, p):
        return p["radius"]

    def n_elements(self, p):
        return 20 * int(p["n"]) ** 2

    def element_size(self, p):
        # mittlere Kantenlänge einer unterteilten Ikosaederkugel ≈ 1,05 R / n
        return 1.05 * p["radius"] / max(int(p["n"]), 1)

    def preview(self, p):
        v, f = icosphere(3)
        return v * p["radius"], f

    def section(self, p, plane, offset):
        r2 = p["radius"] ** 2 - offset**2
        if r2 <= 0:
            return []
        t = np.linspace(0, 2 * np.pi, 121)
        r = math.sqrt(r2)
        return [(r * np.cos(t), r * np.sin(t))]

    def build(self, cb, p, unit_nm, curved=False):
        r = p["radius"] / unit_nm
        n = int(p["n"])
        return cb.quadratic_icosphere(n, r) if curved else cb.make_icosphere(n, r)


@GEOMETRIES.register
class Cube(Geometry):
    id = "cube"
    label = "Würfel"
    description = ("Würfel mit scharfen Kanten. Gradiertes Netz verdichtet zu den Kanten hin. "
                   "Nur ebene Elemente; für Kontraste im Resonanzfenster siehe Prüfung.")
    resolution_key = "n"
    resolution_presets = {"flat": (2, 4, 8)}
    fields = (
        Field("edge", "Kantenlänge", "float", 40.0, "nm", min=1.0, max=10000.0, step=1.0),
        Field("mesh", "Netzart", "choice", "graded", choices=(("graded", "gradiert zu den Kanten (empfohlen)"),
                                                              ("uniform", "gleichmäßig")),
              help="Gradierte Netze halten die Iterationszahl unabhängig von der Kantenauflösung (docs/results_cube.md)."),
        Field("n", "Netzfeinheit n", "int", 4, "", min=1, max=30, step=1,
              help="gleichmäßig: 12 n² Dreiecke; gradiert: 48 (n+1)² Dreiecke (n = L)."),
    )

    def reference_length(self, p):
        return p["edge"] / 2.0  # halbe Kante: der Bibliothekswürfel ist [-1, 1]³

    def bounding_radius(self, p):
        return p["edge"] * math.sqrt(3) / 2.0

    def has_sharp_edges(self, p):
        return True

    def n_elements(self, p):
        n = int(p["n"])
        return 12 * n * n if p["mesh"] == "uniform" else 48 * (n + 1) ** 2

    def element_size(self, p):
        n = int(p["n"])
        return p["edge"] / n if p["mesh"] == "uniform" else p["edge"] / (2 * (n + 1))

    def preview(self, p):
        h = p["edge"] / 2.0
        return box((h, h, h))

    def section(self, p, plane, offset):
        h = p["edge"] / 2.0
        if abs(offset) >= h:
            return []
        return [(np.array([-h, h, h, -h, -h]), np.array([-h, -h, h, h, -h]))]

    def build(self, cb, p, unit_nm, curved=False):
        if curved:
            raise ValueError("Würfel: keine gekrümmten Elemente")
        n = int(p["n"])
        m = cb.make_cube_uniform(n) if p["mesh"] == "uniform" else cb.make_cube_graded(n)
        return cb.translated(m, (0.0, 0.0, 0.0), (p["edge"] / 2.0) / unit_nm)  # [-1,1]³ → Halbkante/unit


@GEOMETRIES.register
class GmshFile(Geometry):
    id = "gmsh"
    label = "Gmsh-Datei"
    description = ("Netz aus einer Gmsh-Datei (ASCII, Version 2.2 oder 4.1; je physikalische Gruppe ein Körper). "
                   "Elemente zweiter Ordnung erlauben gekrümmte Elemente.")
    requires = ("gmsh",)
    supports_curved = True  # tatsächlich nur bei Elementen zweiter Ordnung, siehe can_curve
    fields = (
        Field("file", "Datei (.msh)", "file", "", help="ASCII-Gmsh 2.2 oder 4.1, geschlossene Flächen, "
                                                       "nach außen orientiert."),
        Field("group", "Körper in der Datei", "int", 1, "", min=1, max=99,
              help="Nummer der physikalischen Gruppe in der Reihenfolge der Datei (1, 2, ...). "
                   "Für mehrere Körper aus einer Datei mehrere Körper mit verschiedener Gruppe anlegen."),
        Field("file_unit", "Längeneinheit der Datei", "choice", "nm", choices=tuple((k, k) for k in FILE_UNITS_NM)),
        Field("center", "Auf den Ursprung zentrieren", "bool", True,
              help="Mittelpunkt der Begrenzungsbox in den Ursprung; die Lage setzt dann die Position des Körpers."),
    )
    #: wird von der GUI nach der Prüfung der Datei in ``p['_info']`` abgelegt (Worker-Abfrage ``inspect``)

    @staticmethod
    def _info(p):
        return p.get("_info") or {}

    def _extent(self, p):
        i = self._info(p)
        if not i.get("bbox_min"):
            return None
        return np.array(i["bbox_max"]) - np.array(i["bbox_min"])  # nm

    def reference_length(self, p):
        e = self._extent(p)
        return float(e.max() / 2.0) if e is not None else 20.0

    def bounding_radius(self, p):
        e = self._extent(p)
        return float(np.linalg.norm(e) / 2.0) if e is not None else 20.0

    def has_sharp_edges(self, p):
        return bool(self._info(p).get("sharp", False))

    def n_elements(self, p):
        tri = self._info(p).get("n_triangles") or []
        g = int(p["group"])
        return int(tri[g - 1]) if 1 <= g <= len(tri) else 0

    def element_size(self, p):
        return float(self._info(p).get("hmax_nm", 0.0)) or self.reference_length(p) / 4.0

    def can_curve(self, p):
        return int(self._info(p).get("order", 1)) == 2

    def prepare(self, cb, p):
        """Worker: Datei frisch prüfen (Elementzahl, Ordnung, Größe), unabhängig von den Angaben der GUI."""
        from ..gmshinfo import inspect_gmsh_file

        if not p.get("file") or not os.path.isfile(p["file"]):
            return p  # die Prüfung meldet den Fehler
        info = inspect_gmsh_file(cb, p["file"], FILE_UNITS_NM[p["file_unit"]], with_preview=False)
        return {**p, "_info": info}

    def validate(self, p):
        out = []
        f = p.get("file", "")
        if not f:
            out.append(Issue("error", "Keine Gmsh-Datei gewählt."))
        elif not os.path.isfile(f):
            out.append(Issue("error", f"Datei nicht gefunden: {f}"))
        elif not self._info(p):
            out.append(Issue("warning", "Datei noch nicht geprüft (Größe und Elementzahl unbekannt)."))
        else:
            if int(p["group"]) > len(self._info(p).get("n_triangles", [])):
                out.append(Issue("error", f"Die Datei enthält nur {len(self._info(p)['n_triangles'])} Körper."))
        return out

    def preview(self, p):
        i = self._info(p)
        pv = i.get("preview")
        if pv:
            v = np.array(pv["V"], float)
            return v - np.array(i.get("center_nm", [0, 0, 0])) if p.get("center") else v, np.array(pv["F"], int)
        e = self._extent(p)
        return box(tuple(e / 2.0)) if e is not None else box((10.0, 10.0, 10.0))

    def build(self, cb, p, unit_nm, curved=False):
        scale = FILE_UNITS_NM[p["file_unit"]] / unit_nm
        g = int(p["group"]) - 1
        if curved:
            bodies = cb.read_gmsh_quadratic(p["file"], scale)
        else:
            bodies = cb.read_gmsh(p["file"], scale)
        if g >= len(bodies):
            raise ValueError(f"Gmsh-Datei enthält nur {len(bodies)} Körper (verlangt: Gruppe {g + 1})")
        mesh = bodies[g][1]
        if p["center"]:
            pts = np.asarray((mesh.flat if curved else mesh).points)
            c = 0.5 * (pts.min(axis=0) + pts.max(axis=0))
            mesh = cb.translated(mesh, tuple(-c), 1.0)
        return mesh
