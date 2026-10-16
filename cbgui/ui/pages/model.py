"""Seite „Modell“: Körper, Umgebung, Netz und Genauigkeit – mit 3D-Vorschau und Kostenanzeige."""

from __future__ import annotations

import copy

import numpy as np
import streamlit as st

from ...config import default_body, new_body_id
from ...cost import estimate, fmt_bytes, fmt_seconds
from ...plugins.geometries import FILE_UNITS_NM
from ...plugins.materials import PRESETS
from ...registry import FORMULATIONS, GEOMETRIES, MATERIALS
from .. import preview, state
from ..widgets import issue_list, plotly, render_fields

HOSTS = (("Luft", 1.0), ("Wasser", 1.33), ("Ethanol", 1.36), ("Glas", 1.5), ("Immersionsöl", 1.515))


def _apply_preset(body_id: str, key: str) -> None:
    choice = st.session_state.get(key)
    if not choice:
        return
    label_to = {p[0]: p for p in PRESETS}
    _, mtype, params = label_to[choice]
    for b in state.cfg()["bodies"]:
        if b["id"] == body_id:
            b["material"] = {"type": mtype, "params": dict(params)}
    st.session_state[key] = ""
    st.session_state["gen"] += 1  # alle Widgets lesen die neuen Werte


def _set_host(n: float) -> None:
    state.cfg()["host"]["n"] = n
    st.session_state["gen"] += 1


def _geom_label(gid: str, caps) -> str:
    g = GEOMETRIES.get(gid)
    r = g.unavailable_reason(caps)
    return g.label + (f"  (nicht verfügbar: {r})" if r else "")


def _body_form(c: dict, idx: int, b: dict, caps) -> bool:
    """Formular eines Körpers. True, wenn die Körperliste geändert wurde (dann ``st.rerun``)."""
    bid = b["id"]
    k = lambda *p: state.wkey(bid, *p)  # noqa: E731
    changed = False
    b["label"] = st.text_input("Name", value=b["label"], key=k("label"))
    # Form
    gids = GEOMETRIES.ids()
    cur = b["geometry"]["type"] if b["geometry"]["type"] in gids else gids[0]
    new = st.selectbox("Form", gids, index=gids.index(cur), format_func=lambda x: _geom_label(x, caps), key=k("gtype"))
    if new != b["geometry"]["type"]:
        b["geometry"] = {"type": new, "params": {}}
    G = GEOMETRIES.get(b["geometry"]["type"])
    st.caption(G.description)
    params = render_fields(G.schema(), b["geometry"].get("params", {}), f"{bid}:g:{G.id}")
    if "_info" in b["geometry"].get("params", {}):
        params["_info"] = b["geometry"]["params"]["_info"]
    b["geometry"]["params"] = params
    if G.id == "gmsh":
        _gmsh_info(b, params)
    # Position
    st.markdown("**Lage (Mittelpunkt)**")
    cols = st.columns(3)
    pos = []
    for col, ax, v in zip(cols, "xyz", b["position"], strict=True):
        with col:
            pos.append(st.number_input(f"{ax} (nm)", value=float(v), step=1.0, format="%.2f", key=k("pos", ax)))
    b["position"] = pos
    # Material
    st.markdown("**Material**")
    pkey = k("preset")
    st.selectbox("Schnellauswahl", [""] + [p[0] for p in PRESETS], format_func=lambda x: x or "Auswählen …", key=pkey,
                 on_change=_apply_preset, args=(bid, pkey))
    mids = MATERIALS.ids()
    mcur = b["material"]["type"] if b["material"]["type"] in mids else mids[0]
    mnew = st.selectbox("Materialmodell", mids, index=mids.index(mcur), format_func=lambda x: MATERIALS.get(x).label, key=k("mtype"))
    if mnew != b["material"]["type"]:
        b["material"] = {"type": mnew, "params": {}}
    M = MATERIALS.get(b["material"]["type"])
    b["material"]["params"] = render_fields(M.schema(), b["material"].get("params", {}), f"{bid}:m:{M.id}")
    b["chi"] = st.number_input("Chiralitätsparameter χ (Pasteur-Medium)", value=float(b.get("chi", 0.0)), step=0.001, format="%.4f",
                               key=k("chi"), help="0 = achiral. D = εE + iχH, B = μH − iχE. Chirale Körper: Zirkulardichroismus im "
                                                  "Spektrum mit zirkularer Polarisation.")
    # Aktionen
    a1, a2, _ = st.columns([1, 1, 3])
    with a1:
        if st.button("Duplizieren", key=k("dup")):
            nb = copy.deepcopy(b)
            nb["id"], nb["label"] = new_body_id(), b["label"] + " (Kopie)"
            ref = G().reference_length(G.schema().fill(b["geometry"]["params"]))
            nb["position"] = [b["position"][0] + 3.0 * ref, b["position"][1], b["position"][2]]
            c["bodies"].insert(idx + 1, nb)
            changed = True
    with a2:
        if st.button("Entfernen", key=k("del"), disabled=len(c["bodies"]) <= 1):
            c["bodies"].pop(idx)
            changed = True
    return changed


def _gmsh_info(b: dict, params: dict) -> None:
    path = params.get("file", "")
    if not path:
        return
    unit = FILE_UNITS_NM[params.get("file_unit", "nm")]
    info = state.inspect_gmsh(path, unit)
    pv = st.session_state.setdefault("gmsh_pv", {})
    if info is None:
        st.error("Datei konnte nicht gelesen werden: " + st.session_state.get("inspect_error", "unbekannter Fehler"))
        params.pop("_info", None)
        return
    pv[b["id"]] = info.get("preview")
    params["_info"] = {k: v for k, v in info.items() if k != "preview"}
    ext = np.array(info["bbox_max"]) - np.array(info["bbox_min"])
    st.caption(f"{len(info['tags'])} Körper in der Datei (Dreiecke je Körper: {info['n_triangles']}), Elemente der "
               f"{'zweiten' if info['order'] == 2 else 'ersten'} Ordnung, Ausdehnung {ext[0]:.1f} × {ext[1]:.1f} × {ext[2]:.1f} nm.")


def _bodies(c: dict, caps) -> None:
    n = len(c["bodies"])
    for idx, b in enumerate(list(c["bodies"])):
        G = GEOMETRIES.get(b["geometry"]["type"]) if b["geometry"]["type"] in GEOMETRIES else None
        with st.expander(f"{b['label']}  ·  {G.label if G else '?'}", expanded=(n <= 2)):
            if _body_form(c, idx, b, caps):
                st.rerun()
    st.markdown("---")
    c1, c2 = st.columns([2, 1])
    with c1:
        gid = st.selectbox("Neuer Körper", GEOMETRIES.ids(), format_func=lambda x: GEOMETRIES.get(x).label, key=state.wkey("newgeom"))
    with c2:
        st.write("")
        if st.button("Körper hinzufügen"):
            nb = default_body(len(c["bodies"]) + 1)
            nb["geometry"] = {"type": gid, "params": {}}
            m = state.model()
            if m is not None and m.bodies:
                last = m.bodies[-1]
                g = GEOMETRIES.get(gid)()
                gap = 10.0
                nb["position"] = [float(last.position[0] + last.geometry.bounding_radius(last.gp)
                                        + g.bounding_radius(g.schema().defaults()) + gap), float(last.position[1]), float(last.position[2])]
            c["bodies"].append(nb)
            st.rerun()
    with st.expander("Dimer-Assistent (ersetzt alle Körper durch zwei gleiche Kugeln)"):
        r = st.number_input("Radius (nm)", 1.0, 5000.0, 20.0, 1.0, key=state.wkey("dim_r"))
        gap = st.number_input("Spalt (nm)", 0.1, 5000.0, 2.0, 0.5, key=state.wkey("dim_gap"))
        axis = st.selectbox("Dimerachse", ["x", "y", "z"], key=state.wkey("dim_ax"))
        if st.button("Dimer anlegen"):
            first = copy.deepcopy(c["bodies"][0])
            first["geometry"] = {"type": "sphere", "params": {"radius": r, "n": c["bodies"][0]["geometry"].get("params", {}).get("n", 8)}}
            bodies = []
            for sgn, name in ((-1, "Kugel A"), (+1, "Kugel B")):
                b = copy.deepcopy(first)
                b["id"], b["label"] = new_body_id(), name
                pos = [0.0, 0.0, 0.0]
                pos["xyz".index(axis)] = sgn * (r + gap / 2)
                b["position"] = pos
                bodies.append(b)
            c["bodies"] = bodies
            st.session_state["gen"] += 1
            st.rerun()


def _host(c: dict) -> None:
    st.markdown("**Außenmedium** (homogen, verlustfrei)")
    cols = st.columns(len(HOSTS))
    for col, (name, n) in zip(cols, HOSTS, strict=True):
        with col:
            st.button(f"{name}\n{n:g}", on_click=_set_host, args=(n,), key=state.wkey("host", name))
    c["host"]["n"] = st.number_input("Brechungsindex n", min_value=0.5, max_value=5.0, value=float(c["host"]["n"]), step=0.01,
                                     format="%.3f", key=state.wkey("host_n"))
    c["host"]["chi"] = st.number_input("Chiralitätsparameter χ des Außenmediums", value=float(c["host"].get("chi", 0.0)), step=0.001,
                                       format="%.4f", key=state.wkey("host_chi"),
                                       help="Chirale Lösung (z. B. Zuckerlösung). Dann ist nur zirkulare Polarisation möglich.")


def _apply_resolution(level: int) -> None:
    c = state.cfg()
    el = FORMULATIONS.get(c["formulation"]["type"]).element
    for b in c["bodies"]:
        G = GEOMETRIES.get(b["geometry"]["type"])
        if G.resolution_key and el in G.resolution_presets:
            b["geometry"].setdefault("params", {})[G.resolution_key] = G.resolution_presets[el][level]
    st.session_state["gen"] += 1


def _discretization(c: dict, caps) -> None:
    ids = FORMULATIONS.ids()
    cur = c["formulation"]["type"] if c["formulation"]["type"] in ids else ids[0]

    def label(x):
        F = FORMULATIONS.get(x)
        r = F.unavailable_reason(caps)
        return F.label + (f"  (nicht verfügbar: {r})" if r else "")

    new = st.selectbox("Formulierung", ids, index=ids.index(cur), format_func=label, key=state.wkey("form"))
    if new != c["formulation"]["type"]:
        c["formulation"] = {"type": new, "params": {}}
    F = FORMULATIONS.get(c["formulation"]["type"])
    st.caption(F.description)
    c["formulation"]["params"] = render_fields(F.schema(), c["formulation"].get("params", {}), f"form:{F.id}")
    st.markdown("**Genauigkeit für alle Körper setzen**")
    b1, b2, b3 = st.columns(3)
    b1.button("Entwurf", on_click=_apply_resolution, args=(0,), help="schnell, grob", key=state.wkey("res0"))
    b2.button("Standard", on_click=_apply_resolution, args=(1,), help="ausgewogen", key=state.wkey("res1"))
    b3.button("Fein", on_click=_apply_resolution, args=(2,), help="langsam, genau", key=state.wkey("res2"))
    st.caption("Wirkt auf Körper mit Netzfeinheit n (Kugel, Würfel). Gmsh-Netze bringen ihre Auflösung mit.")


def render() -> None:
    state.init()
    c = state.cfg()
    caps = state.caps()
    st.title("Modell")
    st.caption("Körper, Umgebung und Diskretisierung. Alle Längen in nm.")
    left, right = st.columns([3, 2], gap="large")
    with left:
        t1, t2, t3 = st.tabs(["Körper", "Umgebung", "Netz und Genauigkeit"])
        with t1:
            _bodies(c, caps)
        with t2:
            _host(c)
        with t3:
            _discretization(c, caps)
    with right:
        m = state.model()
        if m is not None and m.bodies:
            plotly(preview.figure(m, st.session_state.get("gmsh_pv")), key=state.wkey("prev3d"))
            e = estimate(m, int((caps or {}).get("threads", 1)))
            a, b = st.columns(2)
            a.metric("Elemente", f"{e['elements']:,}".replace(",", " "))
            b.metric("Unbekannte", f"{e['unknowns']:,}".replace(",", " "))
            a.metric("Speicher ≈", fmt_bytes(e["memory_mb"]))
            b.metric("Zeit je Wellenlänge ≈", fmt_seconds(e["build_s"] + e["solve_s"]))
            st.caption(f"Längeneinheit der Bibliothek: {m.unit_nm:g} nm (Bezugslänge des ersten Körpers).")
        issues = [i for i in state.issues() if i.where not in ("Kosten",) and i.level != "info"]
        if issues:
            with st.expander(f"Prüfung: {len(issues)} Hinweise", expanded=any(i.level == "error" for i in issues)):
                issue_list(issues)
