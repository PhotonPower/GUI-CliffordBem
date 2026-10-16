"""Startseite: Überblick, Vorlagen, letzte Läufe."""

from __future__ import annotations

import streamlit as st

from ... import __version__
from .. import nav, state
from ..widgets import fmt_duration


def _load_template(t: dict) -> None:
    state.set_cfg(t["cfg"])
    nav.go("model")


def render() -> None:
    state.init()
    caps = state.caps()
    st.title("CliffordBem")
    st.markdown("Koordinatenfreie Randelementmethode für die Nano-Optik in der Clifford-Algebra Cl₃(ℂ): "
                "Streuung, Nahfelder und optische Kräfte an Körpern aus beliebigen Materialien, auch chiralen.")
    if caps:
        st.success(f"Bibliothek CliffordBem {caps['version']} verbunden · {caps['threads']} Rechenkern(e) · GUI {__version__}")
    else:
        st.warning("Keine Bibliothek verbunden: Vorschau und Prüfungen funktionieren, Rechnen nicht. "
                   "Siehe „Bibliothek und Fahrplan“.")
    st.subheader("So geht es")
    a, b, c, d, e = st.columns(5)
    for col, (name, title, text) in zip(
            (a, b, c, d, e),
            (("model", "1 · Modell", "Körper, Material, Umgebung, Netz"), ("excitation", "2 · Anregung", "Wellenlänge, Richtung, Polarisation"),
             ("observables", "3 · Auswertung", "Spektrum, Nahfeld, Kräfte"), ("run", "4 · Berechnung", "Prüfen, starten, verfolgen"),
             ("results", "5 · Ergebnisse", "Abbildungen und Export")), strict=True):
        with col, st.container(border=True):
            st.markdown(f"**{title}**")
            st.caption(text)
            if nav.PAGES.get(name):
                st.page_link(nav.PAGES[name], label="Öffnen")
    st.subheader("Mit einer Vorlage beginnen")
    tpl = state.templates()
    cols = st.columns(3)
    for i, t in enumerate(tpl):
        with cols[i % 3], st.container(border=True):
            st.markdown(f"**{t['title']}**")
            st.caption(t["text"])
            st.button("Vorlage laden", key=f"tpl{i}", on_click=_load_template, args=(t,))
    st.subheader("Zuletzt gerechnet")
    runs = state.runs()[:5]
    if not runs:
        st.caption("Noch keine Läufe.")
    for r in runs:
        s = r["status"]
        st.write(f"`{r['name']}` – {r['state']}" + (f", {fmt_duration(s.get('wall_s'))}" if s.get("wall_s") else ""))
