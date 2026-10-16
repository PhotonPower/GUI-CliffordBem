"""Zustand der Streamlit-Sitzung: das Arbeitsmodell, zwischengespeicherte Abfragen an den Worker, Vorlagen.

Das Arbeitsmodell ist ein einziges Dictionary (``cbgui.config``) in ``st.session_state['cfg']``. Wird es als Ganzes
ersetzt (Vorlage, Laden, „als Vorlage übernehmen“), erhöht ``set_cfg`` den Zähler ``gen``; er steckt in allen
Widget-Schlüsseln, damit die Widgets die neuen Werte übernehmen statt ihren alten Zustand zu behalten.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import streamlit as st

from .. import bridge, store
from ..checks import collect_issues
from ..config import default_config, loads_config, migrate
from ..model import Model, resolve
from ..registry import load_plugins

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def init() -> None:
    load_plugins()
    ss = st.session_state
    ss.setdefault("cfg", default_config())
    ss.setdefault("gen", 0)
    ss.setdefault("current_run", None)


def cfg() -> dict:
    init()
    return st.session_state["cfg"]


def set_cfg(new: dict) -> None:
    st.session_state["cfg"] = migrate(copy.deepcopy(new))
    st.session_state["gen"] += 1


def gen() -> int:
    init()
    return st.session_state["gen"]


def wkey(*parts) -> str:
    """Widget-Schlüssel, der bei einem Austausch des Modells wechselt."""
    return ":".join([str(gen()), *map(str, parts)])


# -- Bibliothek --------------------------------------------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Bibliothek wird abgefragt …")
def _capabilities(_token: int) -> dict | None:
    return bridge.capabilities()


def caps(refresh: bool = False) -> dict | None:
    if refresh:
        st.session_state["caps_token"] = st.session_state.get("caps_token", 0) + 1
    return _capabilities(st.session_state.get("caps_token", 0))


@st.cache_data(show_spinner=False)
def _material_eps(mtype: str, params_json: str, lam: float) -> complex | None:
    try:
        r = bridge.query("material_eps", {"type": mtype, "params": json.loads(params_json), "lams": [lam]}, timeout=60)
        return complex(r["eps_re"][0], r["eps_im"][0])
    except (bridge.WorkerError, KeyError, IndexError):
        return None


def eps_lookup(model: Model):
    """ε(λ) je Körper: ohne Bibliothek direkt, sonst über den Worker (zwischengespeichert)."""

    def look(i: int, lam: float) -> complex | None:
        b = model.bodies[i]
        v = b.material.eps_numpy(b.mp, lam)
        if v is not None:
            return v
        if caps() is None:
            return None
        return _material_eps(b.material.id, json.dumps(b.mp, sort_keys=True), round(float(lam), 6))

    return look


@st.cache_data(show_spinner="Gmsh-Datei wird geprüft …")
def _inspect(path: str, file_unit_nm: float, mtime: float) -> dict:
    return bridge.query("inspect", {"file": path, "file_unit_nm": file_unit_nm}, timeout=120)


def inspect_gmsh(path: str, file_unit_nm: float) -> dict | None:
    try:
        return _inspect(path, file_unit_nm, Path(path).stat().st_mtime)
    except (bridge.WorkerError, OSError) as e:
        st.session_state["inspect_error"] = str(e)
        return None


# -- Modell und Prüfungen ----------------------------------------------------------------------------------------------
def model() -> Model | None:
    try:
        return resolve(cfg())
    except Exception:  # noqa: BLE001 - die Prüfungen melden den Grund
        return None


def issues():
    c = cfg()
    m = model()
    return collect_issues(m if m is not None else c, caps(), eps_lookup(m) if m is not None else None)


# -- Vorlagen ----------------------------------------------------------------------------------------------------------
def templates() -> list[dict]:
    out = []
    for p in sorted(TEMPLATE_DIR.glob("*.json")):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({"file": p.name, "title": d.pop("_title", p.stem), "text": d.pop("_text", ""), "cfg": d})
        except (OSError, json.JSONDecodeError):
            continue
    return out


def load_json_text(text: str) -> None:
    set_cfg(loads_config(text))


def open_run_as_template(run_dir: Path) -> None:
    c = json.loads((Path(run_dir) / "config.json").read_text(encoding="utf-8"))
    c.pop("resolved", None)
    set_cfg(c)


def runs() -> list[dict]:
    return store.list_runs()
