"""Seite „Anregung“: ebene Welle (Richtung, Polarisation, Wellenlänge) mit Vorschau und Materialwerten."""

from __future__ import annotations

import numpy as np
import streamlit as st

from ...registry import EXCITATIONS
from .. import preview, state
from ..widgets import plotly, render_fields


def render() -> None:
    state.init()
    c = state.cfg()
    caps = state.caps()
    st.title("Anregung")
    left, right = st.columns([3, 2], gap="large")
    with left:
        ids = EXCITATIONS.ids()
        cur = c["excitation"]["type"] if c["excitation"]["type"] in ids else ids[0]
        if len(ids) > 1:
            new = st.selectbox("Art der Anregung", ids, index=ids.index(cur), format_func=lambda x: EXCITATIONS.get(x).label,
                               key=state.wkey("etype"))
            if new != c["excitation"]["type"]:
                c["excitation"] = {"type": new, "params": {}}
        E = EXCITATIONS.get(c["excitation"]["type"])
        r = E.unavailable_reason(caps)
        if r:
            st.error(f"{E.label} ist nicht verfügbar: {r}")
        st.caption(E.description)
        c["excitation"]["params"] = render_fields(E.schema(), c["excitation"].get("params", {}), f"exc:{E.id}")
    with right:
        m = state.model()
        if m is not None:
            plotly(preview.figure(m, st.session_state.get("gmsh_pv"), height=380), key=state.wkey("prev_exc"))
            st.caption("Rot: Einfallsrichtung k, blau: elektrisches Feld (zirkular: Ring).")
    if m is not None:
        st.subheader("Zusammenfassung")
        st.write(m.excitation.describe(m.ep))
        lam = m.excitation.wavelength(m.ep)
        if lam:
            st.write(f"Wellenlänge im Außenmedium: **{lam / m.host_n:.1f} nm** (n = {m.host_n:g}).")
            look = state.eps_lookup(m)
            rows = []
            for b in m.bodies:
                eps = look(b.index, lam)
                if eps is None:
                    rows.append({"Körper": b.label, "Material": b.material.short(b.mp), "ε bei λ": "(Bibliothek nötig)", "n + ik": ""})
                else:
                    n = np.sqrt(complex(eps))
                    n = n if n.imag >= 0 else -n
                    rows.append({"Körper": b.label, "Material": b.material.short(b.mp), "ε bei λ": f"{eps.real:.3f} + {eps.imag:.3f}i",
                                 "n + ik": f"{n.real:.3f} + {n.imag:.3f}i"})
            st.dataframe(rows, hide_index=True)
