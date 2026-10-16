"""Kleine, bibliotheksfreie Netzerzeuger für die 3D-Vorschau (nur numpy)."""

from __future__ import annotations

import numpy as np


def icosphere(subdiv: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Einheitskugel aus einem unterteilten Ikosaeder (nach außen orientiert)."""
    t = (1.0 + 5**0.5) / 2.0
    v = np.array(
        [[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
         [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], float)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    f = np.array(
        [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6],
         [7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10],
         [8, 6, 7], [9, 8, 1]])
    verts = [tuple(x) for x in v]
    index = {x: i for i, x in enumerate(verts)}

    def mid(a: int, b: int) -> int:
        m = (np.array(verts[a]) + np.array(verts[b])) / 2.0
        m /= np.linalg.norm(m)
        key = tuple(np.round(m, 12))
        if key not in index:
            index[key] = len(verts)
            verts.append(tuple(m))
        return index[key]

    for _ in range(subdiv):
        nf = []
        for a, b, c in f:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        f = np.array(nf)
    return np.array(verts), f


def box(half: tuple[float, float, float] = (1.0, 1.0, 1.0)) -> tuple[np.ndarray, np.ndarray]:
    """Quader [-hx, hx] × [-hy, hy] × [-hz, hz] mit 12 Dreiecken (nach außen orientiert)."""
    hx, hy, hz = half
    v = np.array([[-hx, -hy, -hz], [hx, -hy, -hz], [hx, hy, -hz], [-hx, hy, -hz],
                  [-hx, -hy, hz], [hx, -hy, hz], [hx, hy, hz], [-hx, hy, hz]], float)
    f = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [2, 3, 7], [2, 7, 6],
                  [1, 2, 6], [1, 6, 5], [3, 0, 4], [3, 4, 7]])
    return v, f


def arrow_segments(origin, direction, length: float):
    """Linie von origin entlang direction (für Pfeile in der Vorschau): ((x0,y0,z0),(x1,y1,z1))."""
    o = np.asarray(origin, float)
    d = np.asarray(direction, float)
    d = d / np.linalg.norm(d)
    return o, o + length * d
