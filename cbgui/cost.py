"""Grobe Kostenabschätzung (Speicher, Zeit) vor dem Start.

Das Modell skaliert die Messwerte der Bibliothek (``docs/results_performance.md``, ein Kern, g++ -O3):
Speicher ∝ N^p, Aufbau ∝ N^1,3 je Wellenlänge, Iteration ∝ N^1,2. Es ist eine **Größenordnung (Faktor 2)**; der Worker
schreibt die gemessenen Werte in ``summary.json``, damit sich die Referenzwerte der Formulierungen nachführen lassen
(``docs/04_tests.md``, Abschnitt Kalibrierung).
"""

from __future__ import annotations

from .model import Model

BUILD_EXP = 1.3
ITER_EXP = 1.2


def speedup(threads: int) -> float:
    """Gewinn durch OpenMP: die H-Matrix-Produkte skalieren bis etwa 8 Kerne brauchbar, danach flach."""
    t = max(int(threads), 1)
    return 1.0 + 0.8 * (min(t, 12) - 1)


def estimate(model: Model, threads: int = 1) -> dict:
    n = max(model.n_elements(), 1)
    f = model.formulation
    ref = f.cost_reference
    s = n / 1280.0
    memory_mb = ref["memory_mb"] * s**f.cost_exponent
    build_s = ref["build_s"] * s**BUILD_EXP
    iter_s = ref["iter_s"] * s**ITER_EXP
    solve_s = ref["iterations"] * iter_s
    builds = sum(ob.n_builds(op, model) for ob, op in model.observables)
    solves = sum(ob.n_solves(op, model) for ob, op in model.observables)
    total = (builds * build_s + solves * solve_s) / speedup(threads)
    return {
        "elements": n,
        "unknowns": n * f.unknowns_per_element,
        "memory_mb": memory_mb,
        "build_s": build_s / speedup(threads),
        "solve_s": solve_s / speedup(threads),
        "builds": builds,
        "solves": solves,
        "total_s": total,
    }


def fmt_seconds(s: float) -> str:
    if s < 90:
        return f"{s:.0f} s"
    if s < 5400:
        return f"{s / 60:.0f} min"
    return f"{s / 3600:.1f} h"


def fmt_bytes(mb: float) -> str:
    return f"{mb:.0f} MB" if mb < 1024 else f"{mb / 1024:.1f} GB"
