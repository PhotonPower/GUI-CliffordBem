"""Rechenseite: der einzige Ort, der ``cliffordbem`` importiert (docs/adr/0001).

Aufrufe (immer ``python -m cbgui.worker <befehl>``, JSON auf stdout, **letzte Zeile**):

    info                  Version, Fähigkeiten der Bibliothek, Kerne, Speicher, Materialbereiche
    inspect               (stdin JSON) Gmsh-Datei prüfen: Körper, Elemente, Begrenzungsbox, Ordnung
    material_eps          (stdin JSON) ε(λ) eines Materials
    run <run_dir>         ein Lauf (lang): liest config.json, schreibt status/results/summary/report
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from pathlib import Path

import numpy as np

from . import __version__, store
from .base import Solution
from .config import load_config

#: Fähigkeit → Attribut des Moduls ``cliffordbem`` (oder (Klasse, Methode)); GUI und Plugins prüfen gegen diese Schlüssel
FEATURE_PROBES: dict[str, str | tuple[str, str]] = {
    "near_field": "exterior_near_field",
    "forces": "force_on_offset",
    "gmsh": "read_gmsh",
    "gmsh_quadratic": "read_gmsh_quadratic",
    "curved": "CurvedScatteringProblem",
    "curved_layered": "CurvedLayeredScatteringProblem",
    "layered": "LayeredScatteringProblem",
    "thin_layer": "ThinLayerScatteringProblem",
    "two_port": "TwoPortLayerProblem",
    "linear": "LinearScatteringProblem",
    "dipole": "dipole_rates",
    "beams": "BeamField",
    "custom_fields": "CustomField",
    "recycling": ("ScatteringProblem", "use_recycling"),
    "hodlr": ("ScatteringProblem", "use_hodlr_preconditioner"),
}


def load_library():
    import cliffordbem as cb  # noqa: PLC0415 - bewusst erst hier (ADR 0001)

    return cb


def total_memory_gb() -> float:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
    except (ValueError, OSError, AttributeError):
        pass
    try:  # Windows
        import ctypes

        class MS(ctypes.Structure):
            _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("total", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong),
                        ("b", ctypes.c_ulonglong), ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong),
                        ("f", ctypes.c_ulonglong)]

        ms = MS()
        ms.l = ctypes.sizeof(MS)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))  # type: ignore[attr-defined]
        return ms.total / 2**30
    except Exception:  # noqa: BLE001
        return 0.0


def library_info(cb) -> dict:
    feats = {}
    for k, probe in FEATURE_PROBES.items():
        if isinstance(probe, tuple):
            feats[k] = hasattr(getattr(cb, probe[0], None), probe[1])
        else:
            feats[k] = hasattr(cb, probe)
    mats = {}
    for name in ("Au", "Ag"):
        try:
            m = cb.make_material(name)
            mats[name] = [float(m.lambda_min), float(m.lambda_max)]
        except Exception:  # noqa: BLE001
            pass
    try:
        threads = int(cb.omp_threads())
    except Exception:  # noqa: BLE001
        threads = os.cpu_count() or 1
    return {"version": str(cb.__version__), "features": feats, "threads": threads, "cpu_count": os.cpu_count() or 1,
            "memory_gb": round(total_memory_gb(), 1), "materials": mats, "data_dir": str(getattr(cb, "DATA_DIR", "")),
            "gui_version": __version__, "python": sys.version.split()[0]}


# ====================================================================================================================
# Session: alles, was Auswertungen während eines Laufs brauchen
# ====================================================================================================================
class Session:
    """Ein Lauf im Worker: baut die Netze einmal, Probleme je Wellenlänge, und reicht Fortschritt weiter."""

    def __init__(self, cb, model, on_progress=None, log=print):
        self.cb, self.model = cb, model
        self.unit_nm = float(model.unit_nm)
        self.log = log
        self._on_progress = on_progress
        self._span = (0.0, 1.0)
        self._handle = None
        self._handle_key = None
        self._solutions: dict = {}  # Lösungen des aktuellen Problems (gleiche Anregung nicht doppelt lösen)
        self.last_unknowns = 0
        self.timings = {"build_s": 0.0, "solve_s": 0.0, "n_builds": 0, "n_solves": 0}
        self.max_iterations = 0
        self.not_converged = 0
        threads = int(model.solver.get("threads", 0))
        if threads > 0:
            cb.set_num_threads(threads)
        self.lam0 = model.excitation.wavelength(model.ep)
        self.meshes, self.flat_meshes = self._build_meshes()
        self.incident = model.excitation.build(cb, model.ep, self.outer(self.lam0 or 500.0))

    # -- Netze ---------------------------------------------------------------------------------------------------------
    def _build_meshes(self):
        cb, m = self.cb, self.model
        curved = m.curved
        meshes, flats = [], []
        for b in m.bodies:
            mesh = b.geometry.build(cb, b.gp, self.unit_nm, curved)
            mesh = cb.translated(mesh, tuple(float(x) for x in b.position / self.unit_nm), 1.0)
            meshes.append(mesh)
            flats.append(mesh.flat if curved else mesh)
        for i in range(len(flats)):
            for j in range(i + 1, len(flats)):
                cb.require_separated(flats[i], flats[j], 0.0, f"Körper {i + 1} und {j + 1}")
        return meshes, flats

    # -- Medien --------------------------------------------------------------------------------------------------------
    def outer(self, lam_nm: float):
        return self.cb.Medium(eps=complex(self.model.host_n**2), chi=complex(self.model.host_chi))

    def eps_body(self, i: int, lam_nm: float) -> complex:
        b = self.model.bodies[i]
        return complex(b.material.eps(self.cb, b.mp, float(lam_nm)))

    def media(self, lam_nm: float) -> list:
        return [self.cb.Medium(eps=self.eps_body(i, lam_nm), mu=1.0, chi=complex(b.chi)) for i, b in enumerate(self.model.bodies)]

    # -- Probleme und Lösungen ---------------------------------------------------------------------------------------
    def problem(self, lam_nm: float):
        key = round(float(lam_nm), 9)
        if self._handle is not None and self._handle_key == key:
            return self._handle
        self._handle = None  # alten Speicher zuerst freigeben
        self._solutions = {}
        h = self.model.formulation.make_handle(self.cb, self, float(lam_nm))
        self._handle, self._handle_key = h, key
        self.last_unknowns = h.unknowns
        self.timings["build_s"] += h.build_seconds
        self.timings["n_builds"] += 1
        self.log(f"λ = {lam_nm:.2f} nm: {h.unknowns} Unbekannte, H-Matrix {h.hmatrix_bytes / 1e6:.1f} MB, Aufbau {h.build_seconds:.2f} s")
        return h

    def solve(self, handle, incident) -> Solution:
        key = (incident.kind, incident.d, incident.p)
        if handle is self._handle and key in self._solutions:
            return self._solutions[key]
        t0 = time.perf_counter()
        tol, mi = float(self.model.solver.get("tol", 1e-6)), int(self.model.solver.get("max_iter", 1000))
        sol = handle.solve(incident, tol, mi)
        dt = time.perf_counter() - t0
        self.timings["solve_s"] += dt
        self.timings["n_solves"] += 1
        self.max_iterations = max(self.max_iterations, sol.iterations)
        if not sol.extra.get("converged", True):
            self.not_converged += 1
            self.log(f"WARNUNG: GMRES nicht konvergiert (Restfehler {sol.residual:.2e}, {sol.iterations} Iterationen)")
        if handle is self._handle and incident.kind == "plane_wave":
            self._solutions[key] = sol
        return sol

    # -- Fortschritt -------------------------------------------------------------------------------------------------
    def begin(self, start: float, end: float) -> None:
        self._span = (start, end)

    def tick(self, frac: float, msg: str = "") -> None:
        if self._on_progress:
            a, b = self._span
            self._on_progress(a + (b - a) * min(max(frac, 0.0), 1.0), msg)


# ====================================================================================================================
# Befehle
# ====================================================================================================================
def _emit(obj) -> None:
    sys.stdout.write("\n" + json.dumps(obj) + "\n")
    sys.stdout.flush()


def cmd_info(_args) -> dict:
    return library_info(load_library())


def cmd_inspect(payload: dict) -> dict:
    """Gmsh-Datei prüfen. ``payload``: {file, file_unit_nm}."""
    from .gmshinfo import inspect_gmsh_file

    return inspect_gmsh_file(load_library(), payload["file"], float(payload.get("file_unit_nm", 1.0)))


def cmd_material_eps(payload: dict) -> dict:
    from .registry import MATERIALS, load_plugins

    load_plugins()
    cb = load_library()
    mat = MATERIALS.get(payload["type"])()
    p = mat.schema().fill(payload.get("params"))
    eps = np.array([mat.eps(cb, p, float(x)) for x in payload["lams"]], complex)
    return {"eps_re": eps.real.tolist(), "eps_im": eps.imag.tolist()}


def _peak_rss_mb() -> float | None:
    try:
        import resource

        r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return r / 1024.0 if sys.platform != "darwin" else r / 2**20
    except Exception:  # noqa: BLE001
        return None


def cmd_run(run_dir: str) -> None:
    from .checks import collect_issues
    from .model import resolve
    from .registry import load_plugins

    run = Path(run_dir)
    t_start = time.time()
    store.write_status(run, state="building", message="Bibliothek und Netze werden vorbereitet", worker_pid=os.getpid(),
                       started=t_start, progress=0.0)
    last = {"t": 0.0}
    log_lines: list[str] = []

    def log(msg: str) -> None:
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        log_lines.append(line)
        print(line, flush=True)

    def on_progress(frac: float, msg: str) -> None:
        now = time.time()
        if now - last["t"] > 0.4 or frac >= 1.0:
            last["t"] = now
            store.write_status(run, progress=round(float(frac), 4), message=msg)

    try:
        load_plugins()
        cfg = load_config(run / "config.json")
        model = resolve(cfg)
        cb = load_library()
        caps = library_info(cb)
        for b in model.bodies:  # Eingaben, die die Bibliothek braucht (z. B. Gmsh-Datei neu prüfen), frisch aus der Quelle
            b.gp = b.geometry.prepare(cb, b.gp)
        errors = [i for i in collect_issues(model, caps) if i.level == "error"]
        if errors:
            raise ValueError("Prüfung fehlgeschlagen: " + "; ".join(i.msg for i in errors))
        log(f"CliffordBem {caps['version']}, GUI {__version__}, {caps['threads']} Threads")
        session = Session(cb, model, on_progress=on_progress, log=log)
        log(f"Längeneinheit der Bibliothek: {session.unit_nm:g} nm, {model.n_elements()} Elemente, Formulierung {model.formulation.id}")
        # Arbeitsanteile je Auswertung ~ Anzahl der Aufbauten und Lösungen
        weights = [max(1.0, ob.n_builds(op, model) * 3 + ob.n_solves(op, model)) for ob, op in model.observables]
        tot = float(sum(weights)) or 1.0
        results: dict[str, np.ndarray] = {}
        summaries: list = [None] * len(model.observables)
        acc = 0.0
        store.write_status(run, state="solving", message="Rechnung läuft")
        # Auswertungen bei einer Wellenlänge zuerst: sie teilen sich Problemaufbau und Lösung (Session-Cache);
        # Ergebnisse bleiben nach dem ursprünglichen Index geordnet.
        order = sorted(range(len(model.observables)), key=lambda k: model.observables[k][0].n_builds(model.observables[k][1], model) > 1)
        for i in order:
            (ob, op), w = model.observables[i], weights[i]
            session.begin(acc / tot, (acc + w) / tot)
            log(f"Auswertung {i + 1}/{len(model.observables)}: {ob.label}")
            data = ob.compute(session, op)
            acc += w
            for k, v in data.items():
                a = np.asarray(v)
                if a.dtype == object:
                    raise TypeError(f"Auswertung {ob.id}: Schlüssel {k!r} hat keinen speicherbaren Typ")
                results[f"obs{i}__{k}"] = a
            try:
                summaries[i] = {"id": ob.id, "label": ob.label, "metrics": ob.summary(data)}
            except Exception as e:  # noqa: BLE001 - eine fehlerhafte Zusammenfassung stoppt den Lauf nicht
                summaries[i] = {"id": ob.id, "label": ob.label, "metrics": {"Hinweis": f"Zusammenfassung nicht möglich: {e}"}}
        store.write_status(run, state="postprocessing", message="Ergebnisse werden gespeichert", progress=0.99)
        np.savez_compressed(run / "results.npz", **results)
        wall = time.time() - t_start
        rss = _peak_rss_mb()
        summary = {
            "wall_s": wall, "unknowns": session.last_unknowns, "elements": model.n_elements(), "formulation": model.formulation.id,
            "library_version": caps["version"], "gui_version": __version__, "threads": caps["threads"],
            "timings": session.timings, "max_iterations": session.max_iterations, "not_converged": session.not_converged,
            "peak_rss_mb": rss, "observables": summaries, "unit_nm": session.unit_nm,
        }
        (run / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
        (run / "report.txt").write_text(_report(cfg, summary, log_lines), encoding="utf-8")
        store.write_status(run, state="done", message="fertig", progress=1.0, finished=time.time(), wall_s=wall,
                           unknowns=session.last_unknowns, not_converged=session.not_converged)
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc()
        print(tb, file=sys.stderr, flush=True)
        store.write_status(run, state="error", message=f"{type(e).__name__}: {e}", traceback=tb[-4000:], finished=time.time())
        sys.exit(1)


def _report(cfg: dict, summary: dict, log_lines: list[str]) -> str:
    out = [f"CliffordBem-GUI {summary['gui_version']} / Bibliothek {summary['library_version']}", f"Lauf: {cfg.get('name', '')}",
           f"Laufzeit: {summary['wall_s']:.1f} s, {summary['threads']} Threads, Spitzenspeicher "
           + (f"{summary['peak_rss_mb']:.0f} MB" if summary.get("peak_rss_mb") else "unbekannt"),
           f"Elemente: {summary['elements']}, Unbekannte: {summary['unknowns']}, Formulierung: {summary['formulation']}",
           f"Aufbauten: {summary['timings']['n_builds']} ({summary['timings']['build_s']:.1f} s), "
           f"Lösungen: {summary['timings']['n_solves']} ({summary['timings']['solve_s']:.1f} s), "
           f"max. Iterationen: {summary['max_iterations']}, nicht konvergiert: {summary['not_converged']}", ""]
    for o in summary["observables"]:
        out.append(f"== {o['label']}")
        out += [f"   {k}: {v}" for k, v in o["metrics"].items()]
    out += ["", "-- Protokoll --"] + log_lines
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "run":
        cmd_run(rest[0])
        return 0
    payload = json.loads(sys.stdin.read() or "{}") if cmd in ("inspect", "material_eps") else {}
    fn = {"info": cmd_info, "inspect": cmd_inspect, "material_eps": cmd_material_eps}.get(cmd)
    if fn is None:
        print(f"unbekannter Befehl {cmd!r}", file=sys.stderr)
        return 2
    _emit(fn(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
