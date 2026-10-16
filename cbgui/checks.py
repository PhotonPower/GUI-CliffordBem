"""Alle Vorab-Prüfungen eines Modells. Fehler (``error``) sperren den Start, Warnungen und Hinweise nicht.

Regeln stammen aus der Bibliotheksdokumentation (Verweise in den Meldungen: ``docs/…`` des Bibliotheksprojekts).
Die Prüfung läuft in der GUI (jede Eingabeänderung) und noch einmal im Worker vor dem Rechnen.
"""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from .base import Issue
from .cost import estimate, fmt_bytes, fmt_seconds
from .model import Model, resolve

#: Resonanzfenster scharfer rechter Kanten: Kontrast ε_innen/ε_außen in [−3, −1/3] (docs/results_resonance_window.md)
RESONANCE_WINDOW = (-3.0, -1.0 / 3.0)
#: Elementkante größer als λ/MESH_WAVELENGTH_RATIO → Warnung
MESH_WAVELENGTH_RATIO = 5.0


def collect_issues(src, caps: dict | None = None, eps_lookup: Callable[[int, float], complex | None] | None = None) -> list[Issue]:
    try:
        model = src if isinstance(src, Model) else resolve(src)
    except KeyError as e:
        return [Issue("error", f"Konfiguration enthält ein unbekanntes Plugin: {e.args[0]}")]
    except Exception as e:  # noqa: BLE001
        return [Issue("error", f"Konfiguration nicht auswertbar: {type(e).__name__}: {e}")]
    out: list[Issue] = []

    def add(level, msg, where=""):
        out.append(Issue(level, msg, where))

    def schema_errors(plugin, values, where):
        for m in plugin.schema().errors(values):
            add("error", m, where)

    def availability(plugin, where):
        r = plugin.unavailable_reason(caps)
        if r:
            add("error", f"„{plugin.label}“ ist nicht verfügbar: {r}", where)

    # -- Umgebung ----------------------------------------------------------------------------------------------------
    if not (model.host_n > 0 and math.isfinite(model.host_n)):
        add("error", "Brechungsindex des Außenmediums muss positiv sein.", "Umgebung")
    if not model.bodies:
        add("error", "Kein Körper definiert.", "Modell")

    # -- Körper ------------------------------------------------------------------------------------------------------
    for b in model.bodies:
        w = b.label
        g, m = type(b.geometry), type(b.material)
        schema_errors(g, b.gp, w)
        schema_errors(m, b.mp, w)
        availability(g, w)
        availability(m, w)
        out += [Issue(i.level, i.msg, w) for i in b.geometry.validate(b.gp)]
        out += [Issue(i.level, i.msg, w) for i in b.material.validate(b.mp)]
        if not np.all(np.isfinite(b.position)):
            add("error", "Position ist keine gültige Zahl.", w)
        if not math.isfinite(b.chi):
            add("error", "Chiralitätsparameter ist keine gültige Zahl.", w)

    f = type(model.formulation)
    schema_errors(f, model.fp, "Formulierung")
    availability(f, "Formulierung")
    for b in model.bodies:
        out += [Issue(i.level, i.msg, i.where or b.label) for i in model.formulation.supports(b.geometry, b.gp)]

    e = type(model.excitation)
    schema_errors(e, model.ep, "Anregung")
    availability(e, "Anregung")
    out += [Issue(i.level, i.msg, i.where or "Anregung") for i in model.excitation.validate(model.ep, model)]

    if not model.observables:
        add("error", "Keine Auswertung gewählt – es gäbe nichts zu berechnen.", "Auswertung")
    for ob, op in model.observables:
        schema_errors(type(ob), op, f"Auswertung {ob.label}")
        availability(type(ob), f"Auswertung {ob.label}")
        out += [Issue(i.level, i.msg, i.where or f"Auswertung {ob.label}") for i in ob.validate(op, model)]

    if any(isinstance(x, Issue) and x.level == "error" and x.where in ("Modell",) for x in out):
        return out  # ohne Körper ist der Rest sinnlos

    # -- Lage der Körper -----------------------------------------------------------------------------------------------
    for i, a in enumerate(model.bodies):
        for j in range(i + 1, len(model.bodies)):
            b = model.bodies[j]
            dist = float(np.linalg.norm(a.position - b.position))
            ra, rb = a.reference_length, b.reference_length
            ba, bb = a.geometry.bounding_radius(a.gp), b.geometry.bounding_radius(b.gp)
            if dist < ra + rb:
                add("error", f"„{a.label}“ und „{b.label}“ überlappen (Mittelpunktabstand {dist:.1f} nm).", "Modell")
            elif dist < ba + bb:
                add("warning", f"„{a.label}“ und „{b.label}“ liegen so nah, dass sich die Begrenzungskugeln schneiden; "
                               "die Bibliothek prüft beim Start exakt.", "Modell")
            gap = dist - ba - bb
            hs = min(a.geometry.element_size(a.gp), b.geometry.element_size(b.gp))
            if 0 < gap < hs:
                add("warning", f"Spalt zwischen „{a.label}“ und „{b.label}“ ≈ {gap:.1f} nm ist kleiner als die "
                               f"Elementkante ({hs:.1f} nm): Netz verfeinern, sonst ist das Nahfeld im Spalt ungenau.", "Netz")

    # -- Wellenlängen ------------------------------------------------------------------------------------------------
    lams = model.wavelengths()
    if lams:
        lo, hi = min(lams), max(lams)
        for b in model.bodies:
            rng = b.material.lambda_range(b.mp, caps)
            if rng and (lo < rng[0] or hi > rng[1]):
                add("error", f"{b.material.short(b.mp)}: Daten gelten nur von {rng[0]:.0f} bis {rng[1]:.0f} nm "
                             f"(verlangt {lo:.0f}–{hi:.0f} nm).", b.label)
        for b in model.bodies:
            h = b.geometry.element_size(b.gp)
            if h <= 0:
                continue
            if h > lo / model.host_n / MESH_WAVELENGTH_RATIO:
                add("warning", f"Elementkante {h:.1f} nm ist größer als λ/{MESH_WAVELENGTH_RATIO:g} im Außenmedium "
                               f"({lo / model.host_n / MESH_WAVELENGTH_RATIO:.1f} nm bei {lo:.0f} nm): Netz verfeinern.", b.label)
            ev = (eps_lookup(b.index, lo) if eps_lookup else None) or b.material.eps_numpy(b.mp, lo)
            if ev is not None:
                nin = abs(np.sqrt(complex(ev)))
                if nin > 1.0 and h > lo / nin / MESH_WAVELENGTH_RATIO:
                    add("warning", f"Elementkante {h:.1f} nm ist größer als λ/{MESH_WAVELENGTH_RATIO:g} im Körper "
                                   f"(|n| ≈ {nin:.2f}).", b.label)
        # Resonanzfenster scharfer Kanten
        for b in model.bodies:
            if not b.geometry.has_sharp_edges(b.gp):
                continue
            for lam in sorted({lo, hi, lams[0]}):
                ev = (eps_lookup(b.index, lam) if eps_lookup else None) or b.material.eps_numpy(b.mp, lam)
                if ev is None:
                    continue
                c = complex(ev) / model.host_n**2
                if RESONANCE_WINDOW[0] <= c.real <= RESONANCE_WINDOW[1]:
                    add("warning", f"Scharfe Kanten und Kontrast ε/ε_außen = {c.real:.2f} bei {lam:.0f} nm liegen im "
                                   "Resonanzfenster [−3, −1/3]: Eckwellen laufen in die Kante, Ergebnisse und Iterationszahlen "
                                   "können unzuverlässig sein. Abgerundete Kanten mit aufgelöstem Radius verwenden "
                                   "(Bibliothek: docs/results_resonance_window.md, results_roundcube.md).", b.label)
                    break

    # -- Genauigkeit ---------------------------------------------------------------------------------------------------
    if model.formulation.element == "flat":
        for b in model.bodies:
            if b.geometry.is_sphere and int(b.gp.get("n", 99)) < 6:
                add("info", f"Ebene Dreiecke mit n = {b.gp['n']} liefern an der Kugel nur Fehler von einigen Prozent "
                            "(O(h²)). Für Genauigkeit: n ≥ 8 oder Formulierung „gekrümmte Elemente“.", b.label)

    # -- Kosten und Speicher -------------------------------------------------------------------------------------------
    threads = int(model.solver.get("threads", 0)) or int((caps or {}).get("threads", 1))
    c = estimate(model, threads)
    add("info", f"{c['elements']} Elemente, {c['unknowns']} Unbekannte; Speicher ≈ {fmt_bytes(c['memory_mb'])}, "
                f"Rechenzeit ≈ {fmt_seconds(c['total_s'])} (grobe Schätzung, Faktor 2).", "Kosten")
    ram = float((caps or {}).get("memory_gb", 0)) * 1024
    if ram > 0:
        if c["memory_mb"] > ram:
            add("error", f"Geschätzter Speicher {fmt_bytes(c['memory_mb'])} übersteigt den Arbeitsspeicher ({fmt_bytes(ram)}).", "Kosten")
        elif c["memory_mb"] > 0.6 * ram:
            add("warning", f"Geschätzter Speicher {fmt_bytes(c['memory_mb'])} ist mehr als 60 % des Arbeitsspeichers ({fmt_bytes(ram)}).", "Kosten")
    if c["total_s"] > 3600:
        add("warning", f"Die Rechnung dauert voraussichtlich {fmt_seconds(c['total_s'])}.", "Kosten")
    return out


def has_errors(issues: list[Issue]) -> bool:
    return any(i.level == "error" for i in issues)
