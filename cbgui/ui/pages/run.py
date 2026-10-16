"""Seite „Berechnung“: Zusammenfassung, Prüfung, Start, Fortschritt."""

from __future__ import annotations

import copy
import time

import streamlit as st

from ... import __version__, bridge, store
from ...checks import has_errors
from ...cost import estimate, fmt_bytes, fmt_seconds
from .. import nav, state
from ..widgets import fmt_duration, issue_list


def _summary(m) -> None:
    rows = [("Körper", "; ".join(f"{b.label}: {b.geometry.label} ({b.material.short(b.mp)})" for b in m.bodies)),
            ("Außenmedium", f"n = {m.host_n:g}" + (f", χ = {m.host_chi:g}" if m.host_chi else "")),
            ("Formulierung", m.formulation.label), ("Anregung", m.excitation.describe(m.ep)),
            ("Auswertungen", ", ".join(o.label for o, _ in m.observables) or "–")]
    for k, v in rows:
        st.markdown(f"**{k}:** {v}")


def _progress(run_dir) -> None:
    st_ = store.live_status(run_dir)
    state_name = st_.get("state", "?")
    labels = {"queued": "wartet", "building": "bereitet vor", "solving": "rechnet", "postprocessing": "speichert", "done": "fertig",
              "error": "Fehler", "cancelled": "abgebrochen"}
    st.progress(float(st_.get("progress", 0.0)), text=f"{labels.get(state_name, state_name)}: {st_.get('message', '')}")
    t0 = st_.get("started")
    if t0 and state_name not in store.FINAL:
        st.caption(f"Laufzeit {fmt_duration(time.time() - t0)}")
    if state_name == "error":
        st.error(st_.get("message", "Fehler"))
        if st_.get("traceback"):
            with st.expander("Technische Details"):
                st.code(st_["traceback"])
    return state_name


def _live(run_dir) -> None:
    @st.fragment(run_every=2)
    def frag():
        s = _progress(run_dir)
        if s in store.FINAL:
            st.rerun()
        else:
            if st.button("Abbrechen", key="cancel_run"):
                bridge.cancel(run_dir)
                st.rerun()

    frag()


def render() -> None:
    state.init()
    c = state.cfg()
    caps = state.caps()
    m = state.model()
    st.title("Berechnung")
    if m is None:
        st.error("Das Modell ist unvollständig. Bitte zuerst Modell, Anregung und Auswertung prüfen.")
        issue_list(state.issues())
        return
    _summary(m)
    st.divider()
    issues = state.issues()
    blocked = has_errors(issues)
    issue_list([i for i in issues if i.where != "Kosten"], show_info=True)
    e = estimate(m, int((caps or {}).get("threads", 1)))
    a, b, d, f = st.columns(4)
    a.metric("Unbekannte", f"{e['unknowns']:,}".replace(",", " "))
    b.metric("Speicher ≈", fmt_bytes(e["memory_mb"]))
    d.metric("Zeit ≈", fmt_seconds(e["total_s"]))
    f.metric("Aufbauten / Lösungen", f"{e['builds']} / {e['solves']}")
    if caps is None:
        st.error("Keine Bibliothek erreichbar: Rechnen ist nicht möglich. Hinweise stehen auf der Seite „Bibliothek und Fahrplan“.")
    c["name"] = st.text_input("Name des Laufs", value=c.get("name", "rechnung"), key=state.wkey("runname"))
    current = st.session_state.get("current_run")
    active = bool(current) and store.live_status(current).get("state") not in store.FINAL
    if st.button("▶ Lauf starten", type="primary", disabled=blocked or caps is None or active):
        cfg2 = copy.deepcopy(c)
        cfg2["resolved"] = {"library": caps, "gui_version": __version__, "unit_nm": m.unit_nm, "unknowns": e["unknowns"]}
        run = bridge.start_run(cfg2)
        st.session_state["current_run"] = str(run)
        st.rerun()
    if blocked:
        st.caption("Der Start ist gesperrt, solange Fehler in der Prüfung stehen.")
    if current:
        st.divider()
        st.subheader("Aktueller Lauf")
        from pathlib import Path

        run_dir = Path(current)
        st.caption(run_dir.name)
        s = store.live_status(run_dir).get("state")
        if s in store.FINAL:
            _progress(run_dir)
            if s == "done":
                st.success("Fertig.")
                if st.button("Zu den Ergebnissen"):
                    st.session_state["results_run"] = str(run_dir)
                    nav.go("results")
        else:
            _live(run_dir)
