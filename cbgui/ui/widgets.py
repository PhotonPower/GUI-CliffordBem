"""Generische Widgets: Formulare aus ``Field``-Schemas, Prüfungsliste, Plotly-Anzeige."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from .. import store
from ..base import Issue
from ..params import Field, Schema
from . import state


def _step(f: Field) -> float | int:
    if f.step:
        return int(f.step) if f.kind == "int" else float(f.step)
    return 1 if f.kind == "int" else 0.1


def _label(f: Field) -> str:
    return f"{f.label} ({f.unit})" if f.unit else f.label


def render_field(f: Field, value, key: str):
    """Ein Widget für ``f``; gibt den neuen Wert zurück."""
    if f.kind == "float":
        v = float(value)
        lo, hi = (float(f.min) if f.min is not None else None), (float(f.max) if f.max is not None else None)
        if lo is not None:
            v = max(v, lo)
        if hi is not None:
            v = min(v, hi)
        return st.number_input(_label(f), min_value=lo, max_value=hi, value=v, step=float(_step(f)), format=f.format,
                               help=f.help or None, key=key)
    if f.kind == "int":
        v = int(value)
        lo, hi = (int(f.min) if f.min is not None else None), (int(f.max) if f.max is not None else None)
        if lo is not None:
            v = max(v, lo)
        if hi is not None:
            v = min(v, hi)
        return int(st.number_input(_label(f), min_value=lo, max_value=hi, value=v, step=int(_step(f)), help=f.help or None, key=key))
    if f.kind == "choice":
        vals = [c[0] for c in f.choices]
        labels = {c[0]: c[1] for c in f.choices}
        idx = vals.index(value) if value in vals else 0
        return st.selectbox(f.label, vals, index=idx, format_func=lambda x: labels[x], help=f.help or None, key=key)
    if f.kind == "bool":
        return st.checkbox(f.label, value=bool(value), help=f.help or None, key=key)
    if f.kind == "file":
        up = st.file_uploader(f"{f.label} hochladen", type=["msh", "yml", "yaml"], key=key + ":up", help=f.help or None)
        if up is not None:
            dest = store.uploads_dir() / Path(up.name).name
            dest.write_bytes(up.getvalue())
            value = str(dest)
        return st.text_input(f"{f.label}: Pfad", value=str(value or ""), key=key + ":" + str(hash(value) % 100000),
                             help="Pfad auf dem Rechner, auf dem die GUI läuft; hochgeladene Dateien liegen im Datenordner.")
    return st.text_input(_label(f), value=str(value), help=f.help or None, key=key)


def render_fields(schema: Schema, values: dict, prefix: str) -> dict:
    """Formular für alle sichtbaren Felder; erweiterte Felder in einem Expander. Gibt die neuen Werte zurück."""
    cur = schema.fill(values)
    normal = [f for f in schema.fields if not f.advanced]
    adv = [f for f in schema.fields if f.advanced]
    for f in normal:
        if schema.is_visible(f, cur):
            cur[f.key] = render_field(f, cur[f.key], state.wkey(prefix, f.key))
    shown = [f for f in adv if schema.is_visible(f, cur)]
    if shown:
        with st.expander("Erweitert"):
            for f in shown:
                cur[f.key] = render_field(f, cur[f.key], state.wkey(prefix, f.key))
    return cur


def issue_list(issues: list[Issue], show_info: bool = True) -> None:
    """Fehler, Warnungen und Hinweise untereinander; Fehler zuerst."""
    order = {"error": 0, "warning": 1, "info": 2}
    for i in sorted(issues, key=lambda x: order[x.level]):
        if i.level == "info" and not show_info:
            continue
        txt = f"**{i.where}:** {i.msg}" if i.where else i.msg
        {"error": st.error, "warning": st.warning, "info": st.info}[i.level](txt)


def plotly(fig, key: str | None = None) -> None:
    """``st.plotly_chart`` über die Breite; funktioniert mit alten und neuen Streamlit-Versionen."""
    try:
        st.plotly_chart(fig, width="stretch", key=key)
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key)


def fmt_duration(s: float | None) -> str:
    if s is None:
        return "–"
    s = float(s)
    if s < 90:
        return f"{s:.0f} s"
    if s < 5400:
        return f"{s / 60:.1f} min"
    return f"{s / 3600:.1f} h"
