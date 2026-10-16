"""CliffordBem-GUI – Einstieg: ``streamlit run app.py``."""

from __future__ import annotations

import streamlit as st

from cbgui import __version__
from cbgui.checks import has_errors
from cbgui.config import to_json
from cbgui.cost import estimate, fmt_bytes, fmt_seconds
from cbgui.ui import nav, state
from cbgui.ui.pages import excitation, home, model, observables, results, run, runs
from cbgui.ui.pages import help as help_page

st.set_page_config(page_title="CliffordBem", page_icon="🔬", layout="wide")
state.init()

pages = {
    "home": st.Page(home.render, title="Start", icon="🏠", url_path="start", default=True),
    "model": st.Page(model.render, title="1 · Modell", icon="🧊", url_path="modell"),
    "excitation": st.Page(excitation.render, title="2 · Anregung", icon="🔦", url_path="anregung"),
    "observables": st.Page(observables.render, title="3 · Auswertung", icon="📈", url_path="auswertung"),
    "run": st.Page(run.render, title="4 · Berechnung", icon="⚙️", url_path="berechnung"),
    "results": st.Page(results.render, title="5 · Ergebnisse", icon="📊", url_path="ergebnisse"),
    "runs": st.Page(runs.render, title="Läufe", icon="🗂️", url_path="laeufe"),
    "help": st.Page(help_page.render, title="Bibliothek und Fahrplan", icon="📚", url_path="bibliothek"),
}
nav.PAGES.update(pages)
pg = st.navigation({"": [pages["home"]], "Aufbau": [pages[k] for k in ("model", "excitation", "observables", "run")],
                    "Auswertung": [pages["results"], pages["runs"]], "Info": [pages["help"]]})
pg.run()

# Seitenleiste nach der Seite zeichnen, damit sie den neuesten Stand des Modells zeigt
with st.sidebar:
    st.markdown(f"**{state.cfg().get('name', '')}**")
    caps = state.caps()
    st.caption(f"Bibliothek {caps['version']}" if caps else "Bibliothek: nicht verbunden")
    m = state.model()
    if m is not None:
        issues = state.issues()
        e = estimate(m, int((caps or {}).get("threads", 1)))
        st.caption(f"{len(m.bodies)} Körper · {e['unknowns']:,} Unbekannte".replace(",", " "))
        st.caption(f"≈ {fmt_bytes(e['memory_mb'])} · ≈ {fmt_seconds(e['total_s'])}")
        n_err = sum(i.level == "error" for i in issues)
        n_warn = sum(i.level == "warning" for i in issues)
        if has_errors(issues):
            st.error(f"{n_err} Fehler in der Prüfung")
        elif n_warn:
            st.warning(f"{n_warn} Warnung(en)")
        else:
            st.success("Modell bereit")
    st.divider()
    st.download_button("Konfiguration speichern", to_json(state.cfg()), file_name=f"{state.cfg().get('name', 'modell')}.json",
                       mime="application/json")
    up = st.file_uploader("Konfiguration laden", type=["json"], key="cfg_upload")
    if up is not None:
        sig = (up.name, up.size)
        if st.session_state.get("_last_upload") != sig:
            st.session_state["_last_upload"] = sig
            try:
                state.load_json_text(up.getvalue().decode("utf-8"))
                st.rerun()
            except Exception as e:  # noqa: BLE001
                st.error(f"Datei nicht lesbar: {e}")
    st.caption(f"CliffordBem-GUI {__version__}")
