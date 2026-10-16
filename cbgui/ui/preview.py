"""3D-Vorschau des Modells (Plotly), ohne Bibliothek: Körper, Einfallsrichtung und Polarisation."""

from __future__ import annotations

import numpy as np

from ..model import Model
from ..plugins.excitations import polarization_basis

COLORS = ("#e0b030", "#9aa5b1", "#4c9be8", "#d8574a", "#6fbf73", "#b07cc6")


def body_arrays(model: Model, gmsh_previews: dict | None = None) -> list[tuple[np.ndarray, np.ndarray]]:
    out = []
    for b in model.bodies:
        gp = dict(b.gp)
        pv = (gmsh_previews or {}).get(b.id)
        if pv and gp.get("_info"):
            gp["_info"] = {**gp["_info"], "preview": pv}
        v, f = b.geometry.preview(gp)
        out.append((np.asarray(v, float) + b.position, np.asarray(f, int)))
    return out


def figure(model: Model, gmsh_previews: dict | None = None, show_excitation: bool = True, height: int = 460):
    import plotly.graph_objects as go

    fig = go.Figure()
    arrays = body_arrays(model, gmsh_previews)
    for k, ((v, f), b) in enumerate(zip(arrays, model.bodies, strict=True)):
        fig.add_trace(go.Mesh3d(x=v[:, 0], y=v[:, 1], z=v[:, 2], i=f[:, 0], j=f[:, 1], k=f[:, 2], color=COLORS[k % len(COLORS)],
                                opacity=0.92, flatshading=True, name=b.label, showlegend=True, hoverinfo="name",
                                lighting=dict(ambient=0.55, diffuse=0.7, specular=0.2)))
    allv = np.vstack([a[0] for a in arrays]) if arrays else np.zeros((1, 3))
    lo, hi = allv.min(axis=0), allv.max(axis=0)
    c, size = 0.5 * (lo + hi), float(max(np.max(hi - lo), 1.0))
    if show_excitation:
        d = model.excitation.direction(model.ep)
        if d is not None:
            tail = c - d * 1.35 * size
            head = c - d * 0.75 * size
            fig.add_trace(go.Scatter3d(x=[tail[0], head[0]], y=[tail[1], head[1]], z=[tail[2], head[2]], mode="lines",
                                       line=dict(color="#c0392b", width=6), name="Einfall k", hoverinfo="name"))
            fig.add_trace(go.Cone(x=[head[0]], y=[head[1]], z=[head[2]], u=[d[0]], v=[d[1]], w=[d[2]], sizemode="absolute",
                                  sizeref=0.18 * size, anchor="tip", colorscale=[[0, "#c0392b"], [1, "#c0392b"]], showscale=False,
                                  hoverinfo="skip", showlegend=False))
            pol = getattr(model.excitation, "polarization_vector", lambda p: None)(model.ep)
            mid = 0.5 * (tail + head)
            if pol is not None:
                a, b2 = mid - 0.25 * size * pol, mid + 0.25 * size * pol
                fig.add_trace(go.Scatter3d(x=[a[0], b2[0]], y=[a[1], b2[1]], z=[a[2], b2[2]], mode="lines",
                                           line=dict(color="#2471a3", width=7), name="E-Feld", hoverinfo="name"))
            elif model.excitation.is_circular(model.ep):
                u, v = polarization_basis(d)
                t = np.linspace(0, 2 * np.pi, 40)
                ring = mid[None, :] + 0.18 * size * (np.cos(t)[:, None] * u + np.sin(t)[:, None] * v)
                fig.add_trace(go.Scatter3d(x=ring[:, 0], y=ring[:, 1], z=ring[:, 2], mode="lines",
                                           line=dict(color="#2471a3", width=5), name="zirkular", hoverinfo="name"))
    pad = 0.9 * size
    fig.update_layout(
        height=height, margin=dict(l=0, r=0, t=0, b=0), uirevision="keep", legend=dict(orientation="h", y=-0.02),
        scene=dict(aspectmode="data", xaxis=dict(title="x (nm)", range=[lo[0] - pad, hi[0] + pad]),
                   yaxis=dict(title="y (nm)", range=[lo[1] - pad, hi[1] + pad]), zaxis=dict(title="z (nm)", range=[lo[2] - pad, hi[2] + pad]),
                   camera=dict(eye=dict(x=1.5, y=-1.6, z=0.9))))
    return fig
