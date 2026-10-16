"""Plugin-Registries.

Eine Erweiterung der GUI ist eine dekorierte Klasse, z. B.::

    @GEOMETRIES.register
    class Zylinder(Geometry):
        id = "cylinder"; label = "Zylinder"; fields = (Field(...),)

Module in ``cbgui/plugins/`` werden automatisch importiert; Pakete Dritter können sich über die Entry-Point-Gruppe
``cbgui.plugins`` anmelden. Regel für Plugin-Module: beim Import nur Standardbibliothek und numpy (``cliffordbem``
bekommt der Worker als Argument ``cb``, plotly wird in den Methoden importiert), weil dieselbe Datei von der GUI und
vom Worker geladen wird, deren Python-Umgebungen sich unterscheiden können (docs/adr/0001).
"""

from __future__ import annotations

import importlib
import pkgutil
import re
from typing import ClassVar

from .params import Field, Schema


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


class Plugin:
    id: ClassVar[str] = ""
    label: ClassVar[str] = ""
    description: ClassVar[str] = ""
    fields: ClassVar[tuple[Field, ...]] = ()
    #: Fähigkeiten der Bibliothek, die das Plugin braucht (Schlüssel aus worker.FEATURE_PROBES)
    requires: ClassVar[tuple[str, ...]] = ()
    #: kleinste Bibliotheksversion, z. B. "0.47"
    min_version: ClassVar[str] = ""

    @classmethod
    def schema(cls) -> Schema:
        return Schema(cls.fields)

    @classmethod
    def unavailable_reason(cls, caps: dict | None) -> str | None:
        """None, wenn nutzbar. Ohne erreichbare Bibliothek (caps None) bleibt alles bedienbar (Vorschau, Prüfungen);
        gerechnet wird dann erst, wenn der Worker antwortet."""
        if caps is None:
            return None
        feats = caps.get("features", {})
        missing = [r for r in cls.requires if not feats.get(r)]
        if missing:
            return "Bibliothek ohne: " + ", ".join(missing)
        if cls.min_version and _version_tuple(caps.get("version", "0")) < _version_tuple(cls.min_version):
            return f"benötigt Bibliothek ≥ {cls.min_version} (vorhanden: {caps.get('version', '?')})"
        return None


class Registry:
    def __init__(self, kind: str):
        self.kind = kind
        self._items: dict[str, type[Plugin]] = {}

    def register(self, cls):
        if not cls.id:
            raise ValueError(f"{cls.__name__}: Plugin braucht eine nichtleere `id`")
        if cls.id in self._items and self._items[cls.id] is not cls:
            raise ValueError(f"{self.kind}-Plugin {cls.id!r} doppelt registriert")
        self._items[cls.id] = cls
        return cls

    def get(self, plugin_id: str):
        try:
            return self._items[plugin_id]
        except KeyError:
            raise KeyError(f"unbekanntes {self.kind}-Plugin {plugin_id!r}; vorhanden: {sorted(self._items)}") from None

    def ids(self) -> list[str]:
        return list(self._items)

    def all(self) -> list[type[Plugin]]:
        return list(self._items.values())

    def __contains__(self, plugin_id: str) -> bool:
        return plugin_id in self._items


GEOMETRIES = Registry("Geometrie")
MATERIALS = Registry("Material")
EXCITATIONS = Registry("Anregung")
FORMULATIONS = Registry("Formulierung")
OBSERVABLES = Registry("Auswertung")

REGISTRIES = {
    "geometry": GEOMETRIES,
    "material": MATERIALS,
    "excitation": EXCITATIONS,
    "formulation": FORMULATIONS,
    "observable": OBSERVABLES,
}

_loaded = False


def load_plugins() -> None:
    """Alle Module in ``cbgui.plugins`` und alle Entry Points der Gruppe ``cbgui.plugins`` importieren."""
    global _loaded
    if _loaded:
        return
    from . import plugins

    for m in pkgutil.iter_modules(plugins.__path__):
        importlib.import_module(f"{plugins.__name__}.{m.name}")
    try:
        from importlib.metadata import entry_points

        for ep in entry_points(group="cbgui.plugins"):
            ep.load()
    except Exception:  # noqa: BLE001 - ein defektes Fremd-Plugin darf die GUI nicht stoppen
        import traceback

        traceback.print_exc()
    _loaded = True
