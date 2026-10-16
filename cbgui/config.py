"""Das Arbeitsmodell ist **ein** JSON-fähiges Dictionary mit ``schema_version`` (docs/adr/0004).

Werte stehen in Anzeigeeinheiten (nm, Grad); Plugins rechnen erst bei der Verwendung um. Ein Lauf kopiert das
Dictionary samt den verwendeten Bibliotheksfähigkeiten (``resolved``) in sein Verzeichnis.
"""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

from . import SCHEMA_VERSION

DEFAULT_SOLVER = {"tol": 1e-6, "max_iter": 1000, "threads": 0}


def new_body_id() -> str:
    return "b" + uuid.uuid4().hex[:6]


def default_body(index: int = 1) -> dict:
    return {
        "id": new_body_id(),
        "label": f"Körper {index}",
        "geometry": {"type": "sphere", "params": {}},
        "position": [0.0, 0.0, 0.0],
        "material": {"type": "tabulated", "params": {"name": "Au"}},
        "chi": 0.0,
    }


def default_config() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "name": "neue_rechnung",
        "host": {"n": 1.33, "chi": 0.0},
        "bodies": [default_body(1)],
        "formulation": {"type": "flat", "params": {}},
        "excitation": {"type": "plane_wave", "params": {"wavelength": 530.0}},
        "observables": [{"type": "extinction", "params": {}}],
        "solver": dict(DEFAULT_SOLVER),
    }


def migrate(cfg: dict) -> dict:
    """Ältere Konfigurationen auf den aktuellen Stand heben. Neue Felder: ``SCHEMA_VERSION`` erhöhen und hier einen
    Block ``if v < n:`` ergänzen (siehe docs/03_konventionen.md)."""
    cfg = copy.deepcopy(cfg)
    v = int(cfg.get("schema_version", 0))
    if v > SCHEMA_VERSION:
        raise ValueError(
            f"Konfiguration hat Schema {v}, diese GUI kennt höchstens {SCHEMA_VERSION}. Bitte die GUI aktualisieren."
        )
    base = default_config()
    for k, val in base.items():  # fehlende Abschnitte ergänzen
        cfg.setdefault(k, copy.deepcopy(val))
    cfg["solver"] = {**DEFAULT_SOLVER, **cfg.get("solver", {})}
    for i, b in enumerate(cfg["bodies"], 1):
        b.setdefault("id", new_body_id())
        b.setdefault("label", f"Körper {i}")
        b.setdefault("position", [0.0, 0.0, 0.0])
        b.setdefault("chi", 0.0)
        b.setdefault("material", {"type": "tabulated", "params": {"name": "Au"}})
        b.setdefault("geometry", {"type": "sphere", "params": {}})
    cfg["schema_version"] = SCHEMA_VERSION
    return cfg


def to_json(cfg: dict) -> str:
    return json.dumps(cfg, indent=2, ensure_ascii=False, sort_keys=False)


def save_config(cfg: dict, path: Path) -> None:
    Path(path).write_text(to_json(cfg), encoding="utf-8")


def load_config(path: Path | str) -> dict:
    return migrate(json.loads(Path(path).read_text(encoding="utf-8")))


def loads_config(text: str) -> dict:
    return migrate(json.loads(text))
