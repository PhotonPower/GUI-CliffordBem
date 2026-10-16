"""Run-Verzeichnisse: ein Ordner je Lauf, alles was ein Lauf braucht oder erzeugt liegt darin (docs/adr/0004).

    <runs_dir>/<JJJJMMTT-HHMMSS>_<name>/
        config.json    vollständiger Reproduktionsdatensatz (inkl. ``resolved``: Bibliotheksfähigkeiten)
        status.json    Zustandsautomat, atomar geschrieben von GUI und Worker
        results.npz    Arrays ``obs<i>__<name>`` (i = Index in config.observables)
        summary.json   Kennzahlen je Auswertung, Zeiten, Speicher (Kalibrierung des Kostenmodells)
        report.txt     lesbarer Laufbericht
        run.log        stdout/stderr des Workers

Nur Standardbibliothek und numpy: GUI und Worker laden das Modul.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from pathlib import Path

import numpy as np

STATES = ("queued", "building", "solving", "postprocessing", "done", "error", "cancelled")
FINAL = ("done", "error", "cancelled")


def home_dir() -> Path:
    p = Path(os.environ.get("CBGUI_HOME", Path.home() / "cbgui_data"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def runs_dir() -> Path:
    p = Path(os.environ.get("CBGUI_RUNS_DIR", home_dir() / "runs"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def uploads_dir() -> Path:
    p = home_dir() / "uploads"
    p.mkdir(parents=True, exist_ok=True)
    return p


def new_run_dir(name: str) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "lauf"
    base = runs_dir() / f"{time.strftime('%Y%m%d-%H%M%S')}_{slug}"
    d, i = base, 1
    while d.exists():
        i += 1
        d = Path(f"{base}_{i}")
    d.mkdir(parents=True)
    return d


def write_status(run_dir: Path, **fields) -> dict:
    """``fields`` in status.json einmischen (atomarer Austausch; Leser sehen nie eine halbe Datei)."""
    path = Path(run_dir) / "status.json"
    cur = read_status(run_dir)
    cur.update(fields)
    cur["updated"] = time.time()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cur), encoding="utf-8")
    os.replace(tmp, path)
    return cur


def read_status(run_dir: Path) -> dict:
    try:
        return json.loads((Path(run_dir) / "status.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def pid_alive(pid: int) -> bool | None:
    """True/False, wenn feststellbar, sonst None (Windows ohne psutil)."""
    try:
        import psutil

        return psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except ImportError:
        pass
    if os.name == "nt":
        return None
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def live_status(run_dir: Path) -> dict:
    """Status mit Absturzerkennung: ein Lauf, der nicht abgeschlossen ist, dessen Prozess aber fehlt (beendet,
    Speicher erschöpft, Rechner neu gestartet), gilt als Fehler statt ewig „rechnet“. Ändert die Datei nicht."""
    st = read_status(run_dir)
    if not st or st.get("state") in FINAL:
        return st
    pid = st.get("worker_pid")
    if pid and pid_alive(int(pid)) is False:
        return {**st, "state": "error", "crashed": True,
                "message": "Prozess existiert nicht mehr (abgestürzt, beendet oder Speicher erschöpft?). "
                           f"Letzter Zustand: {st.get('state')}"}
    return st


def list_runs() -> list[dict]:
    out = []
    for d in sorted(runs_dir().iterdir(), reverse=True):
        if d.is_dir() and (d / "config.json").exists():
            st = live_status(d)
            out.append({"dir": d, "name": d.name, "state": st.get("state", "?"), "status": st})
    return out


def delete_run(run_dir: Path) -> None:
    run_dir = Path(run_dir)
    if run_dir.parent.resolve() != runs_dir().resolve():
        raise ValueError("nur Läufe im Laufverzeichnis löschbar")
    shutil.rmtree(run_dir)


def load_results(run_dir: Path) -> list[dict]:
    """``results.npz`` → eine Liste von Dictionaries (je Auswertung); 0-d-Arrays werden zu Python-Werten."""
    path = Path(run_dir) / "results.npz"
    if not path.exists():
        return []
    cfg = json.loads((Path(run_dir) / "config.json").read_text(encoding="utf-8"))
    out: list[dict] = [{} for _ in cfg.get("observables", [])]
    with np.load(path, allow_pickle=False) as z:
        for key in z.files:
            m = re.match(r"obs(\d+)__(.+)$", key)
            if m and int(m.group(1)) < len(out):
                a = z[key]
                out[int(m.group(1))][m.group(2)] = a.item() if a.ndim == 0 else a
    return out


def load_summary(run_dir: Path) -> dict:
    try:
        return json.loads((Path(run_dir) / "summary.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
