"""Gmsh-Datei prüfen (läuft im Worker, ``cb`` ist das Modul ``cliffordbem``). Geteilt von ``worker.cmd_inspect`` und
``GmshFile.prepare``. Ergebnis ist JSON-fähig; ``preview`` (Dreiecke des ersten Körpers) nur bis 6 000 Dreiecke."""

from __future__ import annotations

import numpy as np


def inspect_gmsh_file(cb, path: str, file_unit_nm: float, with_preview: bool = True) -> dict:
    info: dict = {"order": 1}
    try:
        bodies = cb.read_gmsh_quadratic(path, file_unit_nm)
        info["order"] = 2
        flat = [(t, q.flat) for t, q in bodies]
    except Exception:  # noqa: BLE001 - keine Elemente zweiter Ordnung
        flat = cb.read_gmsh(path, file_unit_nm)
    if not flat:
        raise ValueError("Die Datei enthält keine geschlossenen Körper.")
    info["tags"] = [int(t) for t, _ in flat]
    info["n_triangles"] = [len(m) for _, m in flat]
    allp = np.vstack([np.asarray(m.points) for _, m in flat])
    lo, hi = allp.min(axis=0), allp.max(axis=0)
    info["bbox_min"], info["bbox_max"] = lo.tolist(), hi.tolist()
    info["center_nm"] = (0.5 * (lo + hi)).tolist()
    info["hmax_nm"] = float(max(np.max(m.hmax) for _, m in flat))
    m0 = flat[0][1]
    if with_preview and len(m0) <= 6000:
        info["preview"] = {"V": np.asarray(m0.points).tolist(), "F": np.asarray(m0.triangles).tolist()}
    info["sharp"] = _has_sharp_edges(np.asarray(m0.normals), np.asarray(m0.triangles))
    return info


def _has_sharp_edges(normals: np.ndarray, tri: np.ndarray, angle_deg: float = 40.0) -> bool:
    """Kante, wenn die Normalen benachbarter Dreiecke mehr als ``angle_deg`` Grad abweichen."""
    edge: dict = {}
    cos_lim = np.cos(np.radians(angle_deg))
    for t, (a, b, c) in enumerate(tri):
        for e in ((a, b), (b, c), (c, a)):
            key = (min(e), max(e))
            if key in edge:
                if float(normals[t] @ normals[edge[key]]) < cos_lim:
                    return True
            else:
                edge[key] = t
    return False
