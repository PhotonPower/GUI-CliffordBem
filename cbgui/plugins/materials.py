"""Eingebaute Materialien. Zeitkonvention der Bibliothek: e^{-iωt}, Absorption = Im ε > 0, ε = (n + ik)², k ≥ 0."""

from __future__ import annotations

import os

from ..base import Issue, Material
from ..params import Field
from ..registry import MATERIALS

HC_EV_NM = 1239.841984  # h c in eV nm

#: Schnellauswahl in der Oberfläche: (Bezeichnung, Plugin-id, Parameter)
PRESETS = (
    ("Gold (Johnson–Christy)", "tabulated", {"name": "Au"}),
    ("Silber (Johnson–Christy)", "tabulated", {"name": "Ag"}),
    ("Glas (n = 1,5)", "constant_n", {"n": 1.5, "k": 0.0}),
    ("Polystyrol (n = 1,59)", "constant_n", {"n": 1.59, "k": 0.0}),
    ("Siliziumdioxid (n = 1,46)", "constant_n", {"n": 1.46, "k": 0.0}),
    ("Titandioxid (n = 2,5)", "constant_n", {"n": 2.5, "k": 0.0}),
    ("Silizium, grob (n = 3,9 + 0,02i)", "constant_n", {"n": 3.9, "k": 0.02}),
    ("Drude-Gold (grob)", "drude", {"eps_inf": 9.84, "hbar_wp": 9.03, "hbar_gamma": 0.07}),
)


@MATERIALS.register
class Tabulated(Material):
    id = "tabulated"
    label = "Tabellierte Daten"
    description = "Johnson–Christy-Daten für Gold und Silber oder eine Datei im Format von refractiveindex.info (YAML)."
    fields = (
        Field("name", "Material", "choice", "Au",
              choices=(("Au", "Gold (Johnson–Christy)"), ("Ag", "Silber (Johnson–Christy)"),
                       ("file", "Datei (refractiveindex.info, YAML)"))),
        Field("file", "YAML-Datei", "file", "", visible_if=lambda v: v.get("name") == "file"),
    )

    def _spec(self, p):
        return p["file"] if p["name"] == "file" else p["name"]

    def eps(self, cb, p, lam_nm):
        return complex(cb.make_material(self._spec(p)).eps(lam_nm))

    def lambda_range(self, p, caps=None):
        if p["name"] == "file":
            return None
        r = ((caps or {}).get("materials") or {}).get(p["name"])
        return (float(r[0]), float(r[1])) if r else None

    def validate(self, p):
        if p["name"] == "file":
            if not p.get("file"):
                return [Issue("error", "Keine Materialdatei gewählt.")]
            if not os.path.isfile(p["file"]):
                return [Issue("error", f"Materialdatei nicht gefunden: {p['file']}")]
        return []

    def short(self, p):
        return {"Au": "Au", "Ag": "Ag"}.get(p["name"], os.path.basename(p.get("file", "")) or "Datei")


@MATERIALS.register
class ConstantIndex(Material):
    id = "constant_n"
    label = "Konstanter Brechungsindex n + ik"
    description = "Dispersionsfreies Material (Glas, Polystyrol, ...). Absorption: k > 0."
    fields = (
        Field("n", "Realteil n", "float", 1.5, "", min=0.01, max=20.0, step=0.01, format="%.3f"),
        Field("k", "Imaginärteil k (Absorption)", "float", 0.0, "", min=0.0, max=20.0, step=0.01, format="%.3f"),
    )

    def eps_numpy(self, p, lam_nm):
        return complex(p["n"], p["k"]) ** 2

    def eps(self, cb, p, lam_nm):
        return self.eps_numpy(p, lam_nm)

    def short(self, p):
        return f"n={p['n']:g}" + (f"+{p['k']:g}i" if p["k"] else "")


@MATERIALS.register
class ConstantEps(Material):
    id = "constant_eps"
    label = "Konstante Permittivität ε"
    description = "ε = ε′ + iε″ mit ε″ ≥ 0 (Absorption). Negatives ε′ ist erlaubt (metallisch, z. B. −11 + 1,2i)."
    fields = (
        Field("re", "Realteil ε′", "float", -11.0, "", min=-1000.0, max=1000.0, step=0.1, format="%.3f"),
        Field("im", "Imaginärteil ε″", "float", 1.2, "", min=0.0, max=1000.0, step=0.1, format="%.3f"),
    )

    def eps_numpy(self, p, lam_nm):
        return complex(p["re"], p["im"])

    def eps(self, cb, p, lam_nm):
        return self.eps_numpy(p, lam_nm)

    def short(self, p):
        return f"ε={p['re']:g}+{p['im']:g}i"


@MATERIALS.register
class Drude(Material):
    id = "drude"
    label = "Drude-Modell"
    description = "ε(ω) = ε∞ − ωp² / (ω² + iγω), Energien in eV. Einfaches Metallmodell ohne Interbandübergänge."
    fields = (
        Field("eps_inf", "ε∞", "float", 9.84, "", min=1.0, max=100.0, step=0.1),
        Field("hbar_wp", "Plasmaenergie ħωp", "float", 9.03, "eV", min=0.1, max=50.0, step=0.01),
        Field("hbar_gamma", "Dämpfung ħγ", "float", 0.07, "eV", min=0.0, max=5.0, step=0.01),
    )

    def eps_numpy(self, p, lam_nm):
        e = HC_EV_NM / lam_nm
        return complex(p["eps_inf"] - p["hbar_wp"] ** 2 / (e * e + 1j * p["hbar_gamma"] * e))

    def eps(self, cb, p, lam_nm):
        return self.eps_numpy(p, lam_nm)

    def short(self, p):
        return "Drude"
