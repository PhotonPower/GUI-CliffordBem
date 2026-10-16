"""Seite „Läufe“: Archiv, Löschen, Vergleich von Spektren mehrerer Läufe."""

from __future__ import annotations

import json

import numpy as np
import streamlit as st

from ... import bridge, store
from .. import nav, state
from ..widgets import fmt_duration, plotly

STATE_ICON = {"done": "✅ fertig", "error": "❌ Fehler", "cancelled": "⏹ abgebrochen", "queued": "⏳ wartet", "building": "🔧 bereitet vor",
              "solving": "⚙ rechnet", "postprocessing": "💾 speichert"}


def render() -> None:
    state.init()
    st.title("Läufe")
    runs = state.runs()
    if not runs:
        st.info("Noch keine Läufe. Starte einen unter „Berechnung“.")
        return
    rows = []
    for r in runs:
        s = r["status"]
        summ = store.load_summary(r["dir"])
        rows.append({"Lauf": r["name"], "Zustand": STATE_ICON.get(r["state"], r["state"]), "Dauer": fmt_duration(s.get("wall_s")),
                     "Unbekannte": s.get("unknowns") or summ.get("unknowns") or "", "Formulierung": summ.get("formulation", ""),
                     "Bibliothek": summ.get("library_version", "")})
    st.dataframe(rows, hide_index=True)
    names = [r["name"] for r in runs]
    pick = st.selectbox("Lauf auswählen", names, key="runs_pick")
    run = next(r for r in runs if r["name"] == pick)
    d = run["dir"]
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("Ergebnisse ansehen", disabled=run["state"] != "done"):
            st.session_state["results_run"] = str(d)
            nav.go("results")
    with c2:
        if st.button("Als Vorlage übernehmen"):
            state.open_run_as_template(d)
            nav.go("model")
    with c3:
        if run["state"] not in store.FINAL and st.button("Abbrechen"):
            bridge.cancel(d)
            st.rerun()
    with c4:
        confirm = st.checkbox("Löschen bestätigen", key="del_confirm")
        if st.button("Löschen", disabled=not confirm or run["state"] not in store.FINAL):
            store.delete_run(d)
            st.rerun()
    if run["state"] == "error":
        st.error(run["status"].get("message", "Fehler"))
        if run["status"].get("traceback"):
            with st.expander("Technische Details"):
                st.code(run["status"]["traceback"])

    st.divider()
    st.subheader("Spektren vergleichen")
    spec_runs = []
    for r in runs:
        if r["state"] != "done":
            continue
        try:
            cfg = json.loads((r["dir"] / "config.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for i, o in enumerate(cfg.get("observables", [])):
            if o["type"] == "spectrum":
                spec_runs.append((r, i))
    if len(spec_runs) < 1:
        st.caption("Es gibt noch keine Läufe mit Spektrum.")
        return
    labels = [r["name"] for r, _ in spec_runs]
    sel = st.multiselect("Läufe mit Spektrum", labels, default=labels[:2], key="cmp_sel")
    quantity = st.radio("Größe", ["σ_ext (nm²)", "CD (nm²)"], horizontal=True, key="cmp_q")
    if sel:
        import plotly.graph_objects as go

        fig = go.Figure()
        for r, i in spec_runs:
            if r["name"] in sel:
                dd = store.load_results(r["dir"])[i]
                key = "cd_nm2" if quantity.startswith("CD") else "sigma_nm2"
                fig.add_scatter(x=np.asarray(dd["lambda_nm"]), y=np.asarray(dd[key]), mode="lines+markers", name=r["name"])
        fig.update_layout(template="plotly_white", xaxis_title="Wellenlänge (nm)", yaxis_title=quantity, height=420,
                          margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.12))
        plotly(fig, key="cmp_fig")
