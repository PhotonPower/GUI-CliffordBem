"""Seite „Auswertung“: welche Größen berechnet werden, mit ihren Parametern."""

from __future__ import annotations

import streamlit as st

from ...cost import fmt_seconds
from ...registry import OBSERVABLES
from .. import state
from ..widgets import render_fields


def render() -> None:
    state.init()
    c = state.cfg()
    caps = state.caps()
    st.title("Auswertung")
    st.caption("Wähle, was berechnet werden soll. Auswertungen bei einer Wellenlänge teilen sich Aufbau und Lösung des Problems; "
               "ein Spektrum baut das Problem je Wellenlänge neu auf.")
    current = {o["type"]: o for o in c["observables"]}
    new_list = []
    for O in OBSERVABLES.all():
        reason = O.unavailable_reason(caps)
        on = st.checkbox(f"**{O.label}**", value=O.id in current, disabled=bool(reason), key=state.wkey("ob", O.id))
        st.caption(O.description + (f"  \n⚠ nicht verfügbar: {reason}" if reason else ""))
        if on and not reason:
            params = current.get(O.id, {"params": {}}).get("params", {})
            if O.fields:
                with st.container(border=True):
                    params = render_fields(O.schema(), params, f"ob:{O.id}")
            new_list.append({"type": O.id, "params": params})
        st.write("")
    c["observables"] = new_list
    m = state.model()
    if m is not None and m.observables:
        from ...cost import estimate

        e = estimate(m, int((caps or {}).get("threads", 1)))
        st.info(f"Gesamt: {e['builds']} Problemaufbauten und {e['solves']} Lösungen – geschätzt **{fmt_seconds(e['total_s'])}** "
                f"(grobe Schätzung, Faktor 2).")
    elif not new_list:
        st.warning("Keine Auswertung gewählt.")
