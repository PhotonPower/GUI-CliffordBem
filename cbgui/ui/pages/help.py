"""Seite „Bibliothek und Fahrplan“: Version, Fähigkeiten, geladene Plugins, was kommt."""

from __future__ import annotations

import streamlit as st

from ... import __version__, bridge
from ...registry import REGISTRIES
from ...roadmap import ROADMAP, STATUS_TEXT
from .. import state


def render() -> None:
    state.init()
    st.title("Bibliothek und Fahrplan")
    caps = state.caps()
    c1, c2 = st.columns([3, 1])
    with c2:
        if st.button("Neu abfragen"):
            state.caps(refresh=True)
            st.rerun()
    if caps is None:
        st.error("Es ist keine nutzbare CliffordBem-Bibliothek erreichbar. Die GUI zeigt Vorschau und Prüfungen, rechnet aber nicht.")
        why = bridge.library_error()
        if why:
            st.code(why)
        st.markdown(
            "**So bindest du die Bibliothek ein**\n\n"
            "1. Bibliothek bauen: `cmake -S . -B build -DCBEM_BUILD_PYTHON=ON && cmake --build build -j` (Projekt CliffordBem) "
            "oder `pip install .`.\n"
            "2. Falls die Bibliothek in einem anderen Python liegt (z. B. MSYS2): `CBGUI_WORKER_PYTHON` auf diesen Interpreter und "
            "`CBGUI_WORKER_PYTHONPATH` auf `build/python` setzen, GUI neu starten.\n"
            "3. Hier „Neu abfragen“ drücken. Einzelheiten: `docs/01_konzept.md`, `docs/05_bibliotheksschnittstelle.md`.")
    else:
        with c1:
            st.success(f"CliffordBem {caps['version']} · GUI {__version__} · Python {caps['python']}")
        a, b, c = st.columns(3)
        a.metric("Rechenkerne (OpenMP)", caps["threads"])
        b.metric("Arbeitsspeicher", f"{caps['memory_gb']:.0f} GB" if caps["memory_gb"] else "unbekannt")
        c.metric("Materialdaten", ", ".join(caps["materials"]) or "–")
        with st.expander("Fähigkeiten der Bibliothek"):
            st.dataframe([{"Fähigkeit": k, "vorhanden": "✅" if v else "–"} for k, v in sorted(caps["features"].items())], hide_index=True)
    st.subheader("Geladene Plugins")
    rows = []
    for kind, reg in REGISTRIES.items():
        for P in reg.all():
            reason = P.unavailable_reason(caps)
            rows.append({"Art": kind, "id": P.id, "Name": P.label, "Zustand": "✅" if not reason else f"– {reason}"})
    st.dataframe(rows, hide_index=True)
    st.subheader("Fahrplan")
    st.caption("Was die Bibliothek kann und wie weit die GUI dabei ist. Details und Einbaupunkte: `docs/07_roadmap.md`.")
    feats = (caps or {}).get("features", {})
    rows = [{"Bereich": r["area"], "Fähigkeit": r["item"], "Stand": STATUS_TEXT[r["status"]],
             "Bibliothek": ("ja" if feats.get(r["feature"]) else ("nein" if caps and r["feature"] else "")) if r["feature"] else "noch nicht",
             "Einbaupunkt": r["slot"]} for r in ROADMAP]
    st.dataframe(rows, hide_index=True)
