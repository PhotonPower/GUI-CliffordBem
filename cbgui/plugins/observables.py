"""Eingebaute Auswertungen: Extinktion, Spektrum, Nahfeldkarte, optische Kräfte.

``compute`` läuft im Worker und liefert NumPy-Arrays/Zahlen/Zeichenketten; ``figures`` läuft in der GUI aus genau
diesen Daten (ohne Bibliothek). Konvention für Mie-Überlagerungen: die Daten tragen ``mie_radius_nm`` (NaN = keine
Referenz), ``host_n``, ``eps0_*``, sodass die GUI die Referenz ohne den Lauf neu berechnen kann.
"""

from __future__ import annotations

import numpy as np

from ..base import Incident, Issue, Observable
from ..params import Field
from ..registry import OBSERVABLES

PALETTE = ("#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b")
C_LIGHT = 2.99792458e8  # m/s


def _scalar(x):
    """0-d-Arrays und NumPy-Skalare aus results.npz in Python-Werte umwandeln."""
    if isinstance(x, np.ndarray) and x.ndim == 0:
        return x.item()
    return x


def _mie_reference(data, lam, quantity="sigma_ext_nm2"):
    """Mie-Kurve für eine einzelne achirale Kugel oder None."""
    r = float(_scalar(data.get("mie_radius_nm", np.nan)))
    if not np.isfinite(r) or "eps0_re" not in data:
        return None
    from ..reference.mie import mie_sphere

    eps = np.asarray(data["eps0_re"], float) + 1j * np.asarray(data["eps0_im"], float)
    return mie_sphere(eps, float(_scalar(data["host_n"])), r, lam)[quantity]


def _common(session, lam_nm: float) -> dict:
    """Daten, die jede Auswertung für Referenzen und Dokumentation mitschreibt."""
    m = session.model
    b0 = m.bodies[0]
    single_sphere = (len(m.bodies) == 1 and b0.geometry.is_sphere and abs(b0.chi) == 0 and abs(m.host_chi) == 0)
    eps0 = session.eps_body(0, lam_nm)
    return {
        "unit_nm": float(session.unit_nm),
        "host_n": float(m.host_n),
        "host_chi": float(m.host_chi),
        "n_bodies": len(m.bodies),
        "mie_radius_nm": float(b0.geometry.mie_radius(b0.gp)) if single_sphere else float("nan"),
        "eps0_re": np.array([eps0.real]), "eps0_im": np.array([eps0.imag]),
        "unknowns": int(session.last_unknowns),
    }


# ====================================================================================================================
@OBSERVABLES.register
class Extinction(Observable):
    id = "extinction"
    label = "Extinktion bei einer Wellenlänge"
    description = ("Extinktionsquerschnitt σ_ext (optisches Theorem) und Vorwärtsamplitude S(0) für die eingestellte "
                   "Anregung; bei einer Einzelkugel mit Mie-Vergleich.")
    fields = ()

    def n_builds(self, p, model):
        return 1

    def n_solves(self, p, model):
        return 1

    def compute(self, s, p):
        lam = s.lam0
        h = s.problem(lam)
        sol = s.solve(h, s.incident)
        d = _common(s, lam)
        d["unknowns"] = h.unknowns
        u2 = s.unit_nm**2
        d.update({
            "lam_nm": float(lam), "sigma_nm2": sol.sigma_ext * u2, "forward_re": sol.forward.real,
            "forward_im": sol.forward.imag, "iterations": sol.iterations, "residual": sol.residual,
            "converged": bool(sol.extra.get("converged", True)), "hmatrix_mb": h.hmatrix_bytes / 1e6,
            "build_s": h.build_seconds, "excitation": s.incident.label,
        })
        s.tick(1.0, "Extinktion fertig")
        return d

    def summary(self, data):
        sig = float(_scalar(data["sigma_nm2"]))
        out = {"σ_ext": f"{sig:,.1f} nm²".replace(",", " "), "Iterationen": f"{int(_scalar(data['iterations']))}",
               "Restfehler": f"{float(_scalar(data['residual'])):.1e}"}
        r = float(_scalar(data.get("mie_radius_nm", np.nan)))
        if np.isfinite(r):
            out["Q_ext"] = f"{sig / (np.pi * r * r):.4f}"
            ref = _mie_reference(data, float(_scalar(data["lam_nm"])))
            if ref is not None:
                out["Abweichung zu Mie"] = f"{100 * (sig / ref[0] - 1):+.3f} %"
        return out

    def details(self, data):
        sig = float(_scalar(data["sigma_nm2"]))
        rows = [("Wellenlänge", f"{float(_scalar(data['lam_nm'])):.2f} nm"), ("Extinktionsquerschnitt σ_ext", f"{sig:.2f} nm²"),
                ("Vorwärtsamplitude S(0)", f"{float(_scalar(data['forward_re'])):.5g} + {float(_scalar(data['forward_im'])):.5g}i"),
                ("Konvergiert", "ja" if bool(_scalar(data["converged"])) else "NEIN"),
                ("Unbekannte", f"{int(_scalar(data['unknowns']))}"), ("H-Matrix", f"{float(_scalar(data['hmatrix_mb'])):.1f} MB"),
                ("Aufbauzeit", f"{float(_scalar(data['build_s'])):.2f} s")]
        r = float(_scalar(data.get("mie_radius_nm", np.nan)))
        if np.isfinite(r):
            ref = _mie_reference(data, float(_scalar(data["lam_nm"])))
            if ref is not None:
                rows.insert(2, ("Mie (analytisch)", f"{float(ref[0]):.2f} nm²"))
        return rows


# ====================================================================================================================
@OBSERVABLES.register
class Spectrum(Observable):
    id = "spectrum"
    label = "Extinktionsspektrum"
    description = ("Extinktion über einen Wellenlängenbereich, wahlweise für die eingestellte Anregung, unpolarisiert "
                   "oder zirkular (σ₊, σ₋, Zirkulardichroismus), mit Orientierungsmittelung (Lebedev-Richtungen). "
                   "Pro Wellenlänge wird das Problem neu aufgebaut.")
    fields = (
        Field("lam_min", "Wellenlänge von", "float", 450.0, "nm", min=100.0, max=20000.0, step=10.0),
        Field("lam_max", "Wellenlänge bis", "float", 650.0, "nm", min=100.0, max=20000.0, step=10.0),
        Field("n_points", "Anzahl Wellenlängen", "int", 21, "", min=2, max=400, step=1),
        Field("pol", "Polarisation", "choice", "excitation",
              choices=(("excitation", "wie in der Anregung (eine Richtung)"),
                       ("unpolarized", "unpolarisiert (Mittel über zwei Polarisationen)"),
                       ("circular", "zirkular σ₊ und σ₋ (mit CD)"))),
        Field("orient", "Orientierungsmittelung", "choice", 1,
              choices=((1, "keine (Richtung der Anregung)"), (6, "6 Richtungen"), (14, "14 Richtungen"), (26, "26 Richtungen")),
              visible_if=lambda v: v.get("pol") != "excitation",
              help="Lebedev-Richtungen: mittelt über die Orientierung des Teilchens (Lösung in Flüssigkeit). "
                   "Jede Richtung kostet Lösungen."),
    )
    view_fields = (
        Field("quantity", "Größe", "choice", "sigma",
              choices=(("sigma", "Querschnitt σ in nm²"), ("q", "Wirkungsgrad Q = σ/(πR²) (Kugel)"))),
        Field("show_ref", "Mie-Referenz zeigen (Einzelkugel)", "bool", True),
    )

    def wavelengths(self, p, model):
        return [p["lam_min"], p["lam_max"]]

    def _n_dirs(self, p):
        return int(p["orient"]) if p["pol"] != "excitation" else 1

    def n_builds(self, p, model):
        return int(p["n_points"])

    def n_solves(self, p, model):
        per = 1 if p["pol"] == "excitation" else 2
        return int(p["n_points"]) * self._n_dirs(p) * per

    def validate(self, p, model):
        out = []
        if p["lam_max"] <= p["lam_min"]:
            out.append(Issue("error", "„Wellenlänge bis“ muss größer sein als „von“."))
        if model is not None and abs(model.host_chi) > 0 and p["pol"] == "unpolarized":
            out.append(Issue("error", "Chirales Außenmedium: nur zirkulare Polarisation möglich."))
        if model is not None and abs(model.host_chi) > 0 and p["pol"] == "excitation" and not model.excitation.is_circular(model.ep):
            out.append(Issue("error", "Chirales Außenmedium: die Anregung muss zirkular sein."))
        if p["pol"] == "circular" and all(abs(b.chi) == 0 for b in model.bodies) and abs(model.host_chi) == 0:
            out.append(Issue("info", "Kein chirales Material: der Zirkulardichroismus verschwindet (Kontrolle ~ 0)."))
        return out

    def _plan(self, s, p):
        """Liste (Einfall, Gewicht, Kennung) je Wellenlänge."""
        cb = s.cb
        inc0 = s.incident
        if p["pol"] == "excitation":
            return [(inc0, 1.0, "main")]
        orient = self._n_dirs(p)
        if orient == 1:
            dirs, wts = [inc0.d], [1.0]
        else:
            dd, ww = cb.lebedev(orient)
            dirs, wts = [tuple(float(x) for x in d) for d in dd], [float(w) for w in ww]
        plan = []
        for d, w in zip(dirs, wts, strict=False):
            if p["pol"] == "unpolarized":
                u, v = cb.polarization_basis(d)
                for pol in (u, v):
                    plan.append((Incident("plane_wave", d=d, p=tuple(complex(x) for x in pol)), 0.5 * w, "main"))
            else:
                for sg, tag in ((+1, "plus"), (-1, "minus")):
                    pol = tuple(complex(x) for x in cb.circular_polarization(d, sg))
                    plan.append((Incident("plane_wave", d=d, p=pol), w, tag))
        return plan

    def compute(self, s, p):
        lams = np.linspace(p["lam_min"], p["lam_max"], int(p["n_points"]))
        plan = self._plan(s, p)
        u2 = s.unit_nm**2
        n = len(lams)
        out = {k: np.zeros(n) for k in ("sigma_nm2", "sigma_plus_nm2", "sigma_minus_nm2", "cd_nm2", "forward_re", "forward_im",
                                        "residual", "build_s", "eps0_re", "eps0_im")}
        out["iterations"] = np.zeros(n, int)
        converged = True
        for i, lam in enumerate(lams):
            h = s.problem(lam)
            tot = {"main": 0.0, "plus": 0.0, "minus": 0.0}
            S = 0j
            its, res = 0, 0.0
            for inc, w, tag in plan:
                sol = s.solve(h, inc)
                tot[tag] += w * sol.sigma_ext
                S += w * sol.forward * (0.5 if tag in ("plus", "minus") else 1.0)
                its = max(its, sol.iterations)
                res = max(res, sol.residual)
                converged &= bool(sol.extra.get("converged", True))
            if p["pol"] == "circular":
                tot["main"] = 0.5 * (tot["plus"] + tot["minus"])
            out["sigma_nm2"][i] = tot["main"] * u2
            out["sigma_plus_nm2"][i] = tot["plus"] * u2
            out["sigma_minus_nm2"][i] = tot["minus"] * u2
            out["cd_nm2"][i] = (tot["plus"] - tot["minus"]) * u2
            out["forward_re"][i], out["forward_im"][i] = S.real, S.imag
            out["iterations"][i], out["residual"][i], out["build_s"][i] = its, res, h.build_seconds
            e0 = s.eps_body(0, lam)
            out["eps0_re"][i], out["eps0_im"][i] = e0.real, e0.imag
            s.tick((i + 1) / n, f"λ = {lam:.1f} nm ({i + 1}/{n}), {its} Iterationen")
        d = _common(s, lams[0])
        d.update(out)
        d["lambda_nm"] = lams
        d["pol_mode"] = p["pol"]
        d["orient"] = self._n_dirs(p)
        d["converged"] = bool(converged)
        return d

    def summary(self, data):
        lam, sig = np.asarray(data["lambda_nm"]), np.asarray(data["sigma_nm2"])
        k = int(np.argmax(sig))
        out = {"Maximum": f"{sig[k]:,.0f} nm²".replace(",", " "), "bei λ": f"{lam[k]:.1f} nm",
               "max. Iterationen": f"{int(np.max(data['iterations']))}"}
        if str(_scalar(data["pol_mode"])) == "circular":
            cd = np.asarray(data["cd_nm2"])
            j = int(np.argmax(np.abs(cd)))
            out["max. |CD|"] = f"{cd[j]:+.2f} nm² bei {lam[j]:.0f} nm"
        return out

    def figures(self, data, ctx, view):
        import plotly.graph_objects as go

        lam = np.asarray(data["lambda_nm"])
        r = float(_scalar(data.get("mie_radius_nm", np.nan)))
        q_mode = view.get("quantity") == "q" and np.isfinite(r)
        scale = 1.0 / (np.pi * r * r) if q_mode else 1.0
        ylab = "Q_ext = σ/(πR²)" if q_mode else "σ_ext (nm²)"
        fig = go.Figure()
        mode = str(_scalar(data["pol_mode"]))
        fig.add_scatter(x=lam, y=np.asarray(data["sigma_nm2"]) * scale, mode="lines+markers", name="CliffordBem (Mittel)" if mode == "circular" else "CliffordBem",
                        line=dict(color=PALETTE[0]))
        if mode == "circular":
            fig.add_scatter(x=lam, y=np.asarray(data["sigma_plus_nm2"]) * scale, mode="lines", name="σ₊", line=dict(color=PALETTE[1], dash="dot"))
            fig.add_scatter(x=lam, y=np.asarray(data["sigma_minus_nm2"]) * scale, mode="lines", name="σ₋", line=dict(color=PALETTE[2], dash="dot"))
        if view.get("show_ref", True):
            ref = _mie_reference(data, lam)
            if ref is not None:
                fig.add_scatter(x=lam, y=ref * scale, mode="lines", name="Mie (analytisch)", line=dict(color="#555", dash="dash"))
        fig.update_layout(template="plotly_white", xaxis_title="Wellenlänge (nm)", yaxis_title=ylab, height=420,
                          margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.12))
        figs = [fig]
        if mode == "circular":
            f2 = go.Figure()
            f2.add_scatter(x=lam, y=np.asarray(data["cd_nm2"]), mode="lines+markers", name="CD = σ₊ − σ₋", line=dict(color=PALETTE[3]))
            f2.add_hline(y=0, line=dict(color="#999", width=1))
            f2.update_layout(template="plotly_white", xaxis_title="Wellenlänge (nm)", yaxis_title="Δσ = σ₊ − σ₋ (nm²)", height=320,
                             margin=dict(l=10, r=10, t=30, b=10))
            figs.append(f2)
        f3 = go.Figure()
        f3.add_bar(x=lam, y=np.asarray(data["iterations"]), marker_color=PALETTE[5], name="Iterationen")
        f3.update_layout(template="plotly_white", xaxis_title="Wellenlänge (nm)", yaxis_title="GMRES-Iterationen", height=220,
                         margin=dict(l=10, r=10, t=10, b=10))
        figs.append(f3)
        return figs

    def csv(self, data):
        cols = ["lambda_nm", "sigma_nm2", "sigma_plus_nm2", "sigma_minus_nm2", "cd_nm2", "forward_re", "forward_im", "iterations"]
        rows = ["# " + ";".join(cols)]
        arrs = [np.asarray(data[c]) for c in cols]
        for i in range(len(arrs[0])):
            rows.append(";".join(f"{a[i]:.9g}" for a in arrs))
        return "\n".join(rows) + "\n"


# ====================================================================================================================
_PLANE_AXES = {"xy": (0, 1, 2), "xz": (0, 2, 1), "yz": (1, 2, 0)}  # (u, v, Normale)


@OBSERVABLES.register
class NearField(Observable):
    id = "nearfield"
    label = "Nahfeldkarte"
    description = ("Feldverstärkung |E|²/|E₀|² und optische Chiralität in einer Schnittebene außerhalb der Körper "
                   "(Cauchy-Integral der Streuspur, halbanalytische Nahquadratur; ab 2 000 Punkten mit H-Matrix).")
    fields = (
        Field("plane", "Schnittebene", "choice", "xz", choices=(("xz", "xz  (y = const)"), ("xy", "xy  (z = const)"), ("yz", "yz  (x = const)"))),
        Field("offset", "Lage der Ebene (Koordinate der Normalen)", "float", 0.0, "nm", min=-1e5, max=1e5, step=1.0),
        Field("auto", "Ausschnitt automatisch", "bool", True, help="Begrenzungsbox aller Körper plus Rand."),
        Field("center_u", "Mitte u", "float", 0.0, "nm", min=-1e5, max=1e5, visible_if=lambda v: not v.get("auto")),
        Field("center_v", "Mitte v", "float", 0.0, "nm", min=-1e5, max=1e5, visible_if=lambda v: not v.get("auto")),
        Field("width_u", "Breite u", "float", 120.0, "nm", min=1.0, max=1e5, visible_if=lambda v: not v.get("auto")),
        Field("width_v", "Breite v", "float", 80.0, "nm", min=1.0, max=1e5, visible_if=lambda v: not v.get("auto")),
        Field("nu", "Punkte u", "int", 91, "", min=5, max=400, step=1),
        Field("nv", "Punkte v", "int", 61, "", min=5, max=400, step=1),
        Field("own_lambda", "Andere Wellenlänge als die Anregung", "bool", False, advanced=True),
        Field("wavelength", "Wellenlänge", "float", 530.0, "nm", min=100.0, max=20000.0, visible_if=lambda v: v.get("own_lambda")),
    )
    view_fields = (
        Field("quantity", "Größe", "choice", "enh", choices=(("enh", "Feldverstärkung |E|²/|E₀|²"), ("chir", "optische Chiralität C/|C₀|"),
                                                           ("ex", "|E_x|²/|E₀|²"), ("ey", "|E_y|²/|E₀|²"), ("ez", "|E_z|²/|E₀|²"))),
        Field("log", "Logarithmische Skala", "bool", True),
        Field("outline", "Körperumrisse", "bool", True),
    )

    def wavelengths(self, p, model):
        return [p["wavelength"]] if p["own_lambda"] else []

    def n_builds(self, p, model):
        return 1

    def validate(self, p, model):
        out = []
        pts = int(p["nu"]) * int(p["nv"])
        if pts > 60000:
            out.append(Issue("warning", f"{pts} Punkte: das dauert (H-Matrix-Auswertung, Speicher für E und H)."))
        if abs(model.host_chi) > 0 and not model.excitation.is_circular(model.ep):
            out.append(Issue("error", "Chirales Außenmedium: die Anregung muss zirkular sein."))
        return out

    def _window(self, s, p, ui, vi):
        if not p["auto"]:
            return p["center_u"] - p["width_u"] / 2, p["center_u"] + p["width_u"] / 2, p["center_v"] - p["width_v"] / 2, p["center_v"] + p["width_v"] / 2
        lo = np.full(2, np.inf)
        hi = np.full(2, -np.inf)
        for b in s.model.bodies:
            r = b.geometry.bounding_radius(b.gp)
            c = b.position[[ui, vi]]
            lo, hi = np.minimum(lo, c - r), np.maximum(hi, c + r)
        pad = max(0.6 * float(np.max(hi - lo)), 10.0)
        return lo[0] - pad, hi[0] + pad, lo[1] - 0.8 * pad, hi[1] + 0.8 * pad

    def compute(self, s, p):
        ui, vi, ni = _PLANE_AXES[p["plane"]]
        lam = float(p["wavelength"]) if p["own_lambda"] else s.lam0
        h = s.problem(lam)
        sol = s.solve(h, s.incident)
        s.tick(0.25, "Nahfeld wird ausgewertet")
        u0, u1, v0, v1 = self._window(s, p, ui, vi)
        u = np.linspace(u0, u1, int(p["nu"]))
        v = np.linspace(v0, v1, int(p["nv"]))
        U, V = np.meshgrid(u, v)
        pts = np.zeros((U.size, 3))
        pts[:, ui], pts[:, vi], pts[:, ni] = U.ravel(), V.ravel(), p["offset"]
        nf = h.near_field(sol, pts / s.unit_nm)
        bad = np.asarray(nf["inside"]) | np.asarray(nf["too_close"])
        shape = (len(v), len(u))
        E, H = np.asarray(nf["E"]), np.asarray(nf["H"])
        e0 = float(np.sum(np.abs(np.asarray(s.incident.p)) ** 2))
        comp = np.abs(E) ** 2 / e0
        maps = {"enhancement": np.asarray(nf["enhancement"]), "chirality": np.asarray(nf["chirality"]),
                "ex": comp[:, 0], "ey": comp[:, 1], "ez": comp[:, 2]}
        d = _common(s, lam)
        d["unknowns"] = h.unknowns
        for k, a in maps.items():
            d[k] = np.where(bad, np.nan, a).reshape(shape)
        d["E_re"], d["E_im"] = E.real.reshape(shape + (3,)), E.imag.reshape(shape + (3,))
        d["H_re"], d["H_im"] = H.real.reshape(shape + (3,)), H.imag.reshape(shape + (3,))
        d.update({"u_nm": u, "v_nm": v, "invalid": bad.reshape(shape), "plane": p["plane"], "offset_nm": float(p["offset"]),
                  "lam_nm": lam, "iterations": sol.iterations, "converged": bool(sol.extra.get("converged", True)),
                  "excitation": s.incident.label, "sigma_nm2": sol.sigma_ext * s.unit_nm**2})
        # Körperumrisse in der Schnittebene (NaN trennt Linienzüge)
        ou, ov = [], []
        for b in s.model.bodies:
            for (cu, cv) in b.geometry.section(b.gp, p["plane"], p["offset"] - b.position[ni]) or []:
                ou += list(np.asarray(cu) + b.position[ui]) + [np.nan]
                ov += list(np.asarray(cv) + b.position[vi]) + [np.nan]
        d["outline_u"], d["outline_v"] = np.array(ou or [np.nan]), np.array(ov or [np.nan])
        s.tick(1.0, "Nahfeld fertig")
        return d

    def summary(self, data):
        a = np.asarray(data["enhancement"])
        if not np.any(np.isfinite(a)):
            return {"Hinweis": "alle Punkte liegen in oder an Körpern"}
        k = np.unravel_index(np.nanargmax(a), a.shape)
        u, v = np.asarray(data["u_nm"]), np.asarray(data["v_nm"])
        pl = str(_scalar(data["plane"]))
        return {"max. |E|²/|E₀|²": f"{np.nanmax(a):,.1f}".replace(",", " "), f"bei ({pl[0]}, {pl[1]})": f"({u[k[1]]:.1f}, {v[k[0]]:.1f}) nm",
                "Punkte": f"{a.size} ({int(np.sum(np.asarray(data['invalid'])))} verdeckt)"}

    def figures(self, data, ctx, view):
        import plotly.graph_objects as go

        q = view.get("quantity", "enh")
        key = {"enh": "enhancement", "chir": "chirality", "ex": "ex", "ey": "ey", "ez": "ez"}[q]
        z = np.array(data[key], float)
        u, v = np.asarray(data["u_nm"]), np.asarray(data["v_nm"])
        pl = str(_scalar(data["plane"]))
        sym = q == "chir"
        use_log = bool(view.get("log", True)) and not sym
        zz = np.where(z > 0, z, np.nan) if use_log else z
        zz = np.log10(zz) if use_log else zz
        kw = {}
        if sym:
            m = np.nanmax(np.abs(zz)) if np.any(np.isfinite(zz)) else 1.0
            kw.update(zmin=-m, zmax=m, colorscale="RdBu_r", zmid=0)
        else:
            kw.update(colorscale="Inferno")
        label = {"enh": "|E|²/|E₀|²", "chir": "C/|C₀|", "ex": "|E_x|²", "ey": "|E_y|²", "ez": "|E_z|²"}[q]
        fig = go.Figure(go.Heatmap(x=u, y=v, z=zz, colorbar=dict(title=("log₁₀ " if use_log else "") + label), **kw))
        if view.get("outline", True):
            ou, ov = np.asarray(data["outline_u"], float), np.asarray(data["outline_v"], float)
            if np.any(np.isfinite(ou)):
                fig.add_scatter(x=ou, y=ov, mode="lines", line=dict(color="white", width=1.5), hoverinfo="skip", showlegend=False)
        fig.update_layout(template="plotly_white", height=520, margin=dict(l=10, r=10, t=30, b=10),
                          xaxis=dict(title=f"{pl[0]} (nm)", constrain="domain"), yaxis=dict(title=f"{pl[1]} (nm)", scaleanchor="x"),
                          title=f"{label} bei λ = {float(_scalar(data['lam_nm'])):.1f} nm, Ebene {pl}, "
                                f"{ {'xy': 'z', 'xz': 'y', 'yz': 'x'}[pl]} = {float(_scalar(data['offset_nm'])):g} nm")
        return [fig]

    def csv(self, data):
        u, v = np.asarray(data["u_nm"]), np.asarray(data["v_nm"])
        rows = ["# u_nm;v_nm;enhancement;chirality;ex2;ey2;ez2"]
        for j, vv in enumerate(v):
            for i, uu in enumerate(u):
                vals = [data[k][j, i] for k in ("enhancement", "chirality", "ex", "ey", "ez")]
                rows.append(f"{uu:.6g};{vv:.6g};" + ";".join("" if not np.isfinite(x) else f"{x:.9g}" for x in vals))
        return "\n".join(rows) + "\n"


# ====================================================================================================================
@OBSERVABLES.register
class Forces(Observable):
    id = "forces"
    label = "Optische Kräfte"
    description = ("Zeitgemittelte Kraft auf jeden Körper aus dem Maxwellschen Spannungstensor über eine Parallelfläche "
                   "(bei ebenen Elementen zusätzlich die Impulsbilanz im Fernfeld als Kontrolle).")
    fields = (
        Field("intensity", "Intensität der einfallenden Welle", "float", 1.0, "mW/µm²", min=1e-6, max=1e6, format="%.3g",
              help="Poynting-Fluss im Außenmedium. 1 mW/µm² = 100 kW/cm². Die Kraft skaliert linear."),
        Field("delta", "Abstand der Parallelfläche", "float", 0.0, "nm", min=0.0, max=1e4, advanced=True,
              help="0 = automatisch (0,2 Bezugslängen, höchstens ein Viertel des kleinsten Spalts)."),
    )

    def wavelengths(self, p, model):
        return []

    def validate(self, p, model):
        out = []
        if len(model.bodies) > 1:
            out.append(Issue("info", "Mehrere Körper: die Kraft wird je Körper über die eigene Parallelfläche bestimmt "
                                     "(Parallelfläche kleiner als der halbe Spalt)."))
        return out

    def compute(self, s, p):
        cb = s.cb
        lam = s.lam0
        h = s.problem(lam)
        sol = s.solve(h, s.incident)
        s.tick(0.3, "Spannungstensor")
        surfaces = h.body_surfaces()
        u = s.unit_nm
        ref = min(b.reference_length for b in s.model.bodies) / u
        gap = float("inf")
        for i, mi in enumerate(surfaces):
            for j, mj in enumerate(surfaces):
                if i != j:
                    gap = min(gap, float(np.min(cb.distance_to_surface(mi, np.asarray(mj.points), 1e6))))
        delta = p["delta"] / u if p["delta"] > 0 else min(0.2 * ref, 0.25 * gap if np.isfinite(gap) else 1e9)
        F = np.array([h.force_on_body(sol, i, delta) for i in range(len(surfaces))])
        Ff = h.force_far_field(sol)
        # Normierung der Bibliothek: F = σ_pr · ½ ε |E₀|², |E₀|² = |p|²; ε des Außenmediums (achiral) = n²
        e0 = float(np.sum(np.abs(np.asarray(s.incident.p)) ** 2))
        eps_h = s.model.host_n**2
        to_sigma_nm2 = (2.0 / (eps_h * e0)) * u**2  # F_lib → σ_pr in nm²
        intensity = p["intensity"] * 1e-3  # W/µm²
        to_pN = lambda f: f * to_sigma_nm2 * 1e-6 * s.model.host_n * intensity / C_LIGHT * 1e12  # noqa: E731  (nm² → µm²)
        d = _common(s, lam)
        d["unknowns"] = h.unknowns
        d.update({
            "lam_nm": float(lam), "force_lib": F, "force_pN": to_pN(F), "sigma_pr_nm2": F * to_sigma_nm2,
            "total_pN": to_pN(F.sum(axis=0)), "delta_nm": delta * u, "intensity_mW_um2": float(p["intensity"]),
            "body_labels": np.array([b.label for b in s.model.bodies]), "sigma_ext_nm2": sol.sigma_ext * u**2,
            "iterations": sol.iterations, "excitation": s.incident.label, "direction": np.asarray(s.incident.d),
        })
        if Ff is not None:
            d["farfield_total_pN"] = to_pN(Ff)
            d["farfield_total_lib"] = Ff
        s.tick(1.0, "Kräfte fertig")
        return d

    def summary(self, data):
        t = np.asarray(data["total_pN"])
        out = {"Gesamtkraft": "(" + ", ".join(f"{x:+.3g}" for x in t) + ") pN"}
        if "farfield_total_pN" in data:
            f = np.asarray(data["farfield_total_pN"])
            ref = max(np.linalg.norm(f), 1e-300)
            out["Fernfeld-Impulsbilanz"] = "(" + ", ".join(f"{x:+.3g}" for x in f) + ") pN"
            out["Abweichung"] = f"{100 * np.linalg.norm(t - f) / ref:.2f} %"
        return out

    def figures(self, data, ctx, view):
        import plotly.graph_objects as go

        F = np.asarray(data["force_pN"])
        labels = [str(x) for x in np.asarray(data["body_labels"])]
        fig = go.Figure()
        for k, (ax, c) in enumerate(zip("xyz", PALETTE, strict=False)):
            fig.add_bar(x=labels, y=F[:, k], name=f"F_{ax}", marker_color=c)
        fig.update_layout(template="plotly_white", barmode="group", height=380, yaxis_title="Kraft (pN)",
                          margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=1.12),
                          title=f"Optische Kraft je Körper bei {float(_scalar(data['intensity_mW_um2'])):g} mW/µm²")
        return [fig]

    def csv(self, data):
        F = np.asarray(data["force_pN"])
        rows = ["# body;Fx_pN;Fy_pN;Fz_pN"]
        for lab, f in zip(np.asarray(data["body_labels"]), F, strict=False):
            rows.append(f"{lab};" + ";".join(f"{x:.9g}" for x in f))
        return "\n".join(rows) + "\n"
