"""Die einzige Verbindung der GUI zur Rechenseite: Unterprozesse und Dateien (docs/adr/0001).

Umgebungsvariablen (alle optional):
  CBGUI_WORKER_PYTHON       Interpreter mit ``cliffordbem`` (Standard: der der GUI), z. B. C:/msys64/ucrt64/bin/python.exe
  CBGUI_WORKER_PYTHONPATH   zusätzlicher PYTHONPATH dafür, z. B. build/python
  CBGUI_HOME                Datenordner (Läufe, Uploads), Standard ~/cbgui_data
  CBGUI_RUNS_DIR            nur die Läufe woanders speichern

Ein Fernstart (Server) = ``worker_argv`` und ``start_run`` austauschen; der Vertrag bleibt das Laufverzeichnis.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from . import store
from .config import save_config

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class WorkerError(RuntimeError):
    pass


def worker_python() -> str:
    return os.environ.get("CBGUI_WORKER_PYTHON", sys.executable)


def worker_env() -> dict:
    env = os.environ.copy()
    extra = os.environ.get("CBGUI_WORKER_PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(p for p in (str(PROJECT_ROOT), extra, env.get("PYTHONPATH", "")) if p)
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def worker_argv(*args: str) -> list[str]:
    return [worker_python(), "-m", "cbgui.worker", *args]


def query(cmd: str, payload: dict | None = None, timeout: float = 120.0) -> dict:
    """Kurzen Worker-Befehl ausführen und das JSON der letzten Ausgabezeile zurückgeben."""
    try:
        r = subprocess.run(worker_argv(cmd), input=json.dumps(payload or {}), capture_output=True, text=True,
                           timeout=timeout, env=worker_env(), cwd=PROJECT_ROOT)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise WorkerError(f"Worker nicht startbar: {e}") from e
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()[-1:] or ["?"]
        raise WorkerError(f"Worker-Fehler: {tail[0]}")
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    try:
        return json.loads(lines[-1])
    except (IndexError, json.JSONDecodeError) as e:
        raise WorkerError("Worker lieferte keine gültige Antwort") from e


def capabilities() -> dict | None:
    """Fähigkeiten der Bibliothek oder None, wenn keine nutzbare ``cliffordbem`` erreichbar ist (die GUI zeigt dann
    Vorschau und Prüfungen, rechnet aber nicht)."""
    try:
        return query("info", timeout=90)
    except WorkerError:
        return None


def library_error() -> str:
    """Grund, warum die Bibliothek nicht erreichbar ist (für die Hilfeseite)."""
    try:
        r = subprocess.run(worker_argv("info"), capture_output=True, text=True, timeout=90, env=worker_env(), cwd=PROJECT_ROOT)
        return (r.stderr or r.stdout).strip().splitlines()[-1] if r.returncode else ""
    except Exception as e:  # noqa: BLE001
        return str(e)


def start_run(cfg: dict) -> Path:
    """Laufverzeichnis anlegen und den Worker abgekoppelt starten."""
    run_dir = store.new_run_dir(cfg.get("name", "lauf"))
    save_config(cfg, run_dir / "config.json")
    store.write_status(run_dir, state="queued", message="in der Warteschlange", progress=0.0)
    log = open(run_dir / "run.log", "ab")  # noqa: SIM115 - bleibt für den Kindprozess offen
    kw: dict = {}
    if os.name == "nt":
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS
    else:
        kw["start_new_session"] = True
    p = subprocess.Popen(worker_argv("run", str(run_dir)), stdout=log, stderr=subprocess.STDOUT, cwd=PROJECT_ROOT,
                         env=worker_env(), **kw)
    store.write_status(run_dir, worker_pid=p.pid)
    return run_dir


def _kill_tree(pid: int) -> None:
    try:
        import psutil

        proc = psutil.Process(pid)
        for c in proc.children(recursive=True):
            c.kill()
        proc.kill()
    except ImportError:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, check=False)
        else:
            os.killpg(os.getpgid(pid), signal.SIGKILL)
    except Exception:  # noqa: BLE001 - Prozess existiert schon nicht mehr
        pass


def cancel(run_dir: Path) -> None:
    st = store.read_status(run_dir)
    if st.get("state") in store.FINAL:
        return
    if st.get("worker_pid"):
        _kill_tree(int(st["worker_pid"]))
    store.write_status(run_dir, state="cancelled", message="vom Benutzer abgebrochen")
