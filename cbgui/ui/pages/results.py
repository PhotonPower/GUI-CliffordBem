"""Seite „Ergebnisse“: Kennzahlen, Abbildungen, Export, Übernahme als Vorlage."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ... import store
from ...params import Schema
from ...registry import OBSERVABLES
from .. import nav, state
from ..widgets import fmt_duration, plotly, render_fields


def _done_runs() -> list[dict]:
    return [r for r in state.runs() if r["state"] == "done"]


def render() -> None:
    state.init()
    st.title("Ergebnisse")
    runs = _done_runs()
    if not runs:
        st.info("Noch kein abgeschlossener Lauf. Starte einen unter „Berechnung“.")
        return
    names = [r["name"] for r in runs]
    want = st.session_state.get("results_run") or st.session_state.get("current_run")
    idx = names.index(Path(want).name) if want and Path(want).name in names else 0
    pick = st.selectbox("Lauf", names, index=idx, key="results_pick")
    run = next(r for r in runs if r["name"] == pick)["dir"]
    cfg = json.loads((run / "config.json").read_text(encoding="utf-8"))
    summary = store.load_summary(run)
    data = store.load_results(run)

    a, b, c, d = st.columns(4)
    a.metric("Laufzeit", fmt_duration(summary.get("wall_s")))
    b.metric("Unbekannte", f"{summary.get('unknowns', 0):,}".replace(",", " "))
    c.metric("max. Iterationen", summary.get("max_iterations", "–"))
    d.metric("Spitzenspeicher", f"{summary['peak_rss_mb']:.0f} MB" if summary.get("peak_rss_mb") else "–")
    if summary.get("not_converged"):
        st.warning(f"{summary['not_converged']} Lösung(en) sind nicht auf die gewünschte Toleranz konvergiert. "
                   "Ergebnisse mit Vorsicht verwenden (Toleranz oder Iterationszahl erhöhen, Netz prüfen).")

    ctx = {"cfg": cfg, "summary": summary}
    obs = cfg.get("observables", [])
    if not obs:
        return
    labels = []
    for o in obs:
        labels.append(OBSERVABLES.get(o["type"]).label if o["type"] in OBSERVABLES else o["type"])
    tabs = st.tabs(labels)
    for i, (tab, o) in enumerate(zip(tabs, obs, strict=True)):
        with tab:
            if o["type"] not in OBSERVABLES:
                st.error(f"Auswertung „{o['type']}“ ist in dieser GUI-Version nicht vorhanden.")
                continue
            O = OBSERVABLES.get(o["type"])()
            d_i = data[i] if i < len(data) else {}
            if not d_i:
                st.warning("Keine Daten für diese Auswertung.")
                continue
            metrics = O.summary(d_i)
            if metrics:
                cols = st.columns(min(len(metrics), 4))
                for k, (key, val) in enumerate(metrics.items()):
                    cols[k % len(cols)].metric(key, val)
            det = O.details(d_i)
            if det:
                with st.expander("Einzelheiten"):
                    st.dataframe([{"Größe": k, "Wert": v} for k, v in det], hide_index=True)
            if d_i.get("excitation"):
                st.caption(f"Anregung: {d_i['excitation']}")
            view = {}
            if O.view_fields:
                with st.container(border=True):
                    view = render_fields(Schema(O.view_fields), {}, f"view:{run.name}:{i}")
            try:
                for j, fig in enumerate(O.figures(d_i, ctx, view)):
                    plotly(fig, key=f"fig:{run.name}:{i}:{j}")
            except Exception as e:  # noqa: BLE001
                st.error(f"Abbildung nicht möglich: {e}")
            csv = O.csv(d_i)
            if csv:
                st.download_button("Tabelle (CSV)", csv, file_name=f"{run.name}_{o['type']}.csv", mime="text/csv", key=f"csv{i}")

    st.divider()
    x1, x2, x3, x4 = st.columns(4)
    with x1:
        if (run / "results.npz").exists():
            st.download_button("Rohdaten (npz)", (run / "results.npz").read_bytes(), file_name=f"{run.name}.npz", key="dl_npz")
    with x2:
        st.download_button("Konfiguration (JSON)", (run / "config.json").read_bytes(), file_name=f"{run.name}.json", key="dl_cfg")
    with x3:
        if (run / "report.txt").exists():
            st.download_button("Laufbericht", (run / "report.txt").read_bytes(), file_name=f"{run.name}_bericht.txt", key="dl_rep")
    with x4:
        if st.button("Als Vorlage übernehmen", help="Lädt die Konfiguration dieses Laufs in die Modellseiten."):
            state.open_run_as_template(run)
            nav.go("model")
    if (run / "report.txt").exists():
        with st.expander("Laufbericht"):
            st.code((run / "report.txt").read_text(encoding="utf-8"))
