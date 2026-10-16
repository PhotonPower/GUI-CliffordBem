import copy

from cbgui import config
from cbgui.checks import collect_issues, has_errors
from cbgui.cost import estimate, speedup
from cbgui.model import resolve

CAPS = {"version": "0.63.0", "features": {"curved": True, "gmsh": True, "forces": True, "near_field": True}, "threads": 4,
        "memory_gb": 16.0, "materials": {"Au": [187.9, 1937.0], "Ag": [187.9, 1937.0]}}


def msgs(cfg, level=None, caps=CAPS, **kw):
    return [i.msg for i in collect_issues(cfg, caps, **kw) if level is None or i.level == level]


def base():
    c = config.default_config()
    c["bodies"][0]["geometry"]["params"] = {"radius": 20.0, "n": 8}
    return c


def test_default_is_clean():
    assert not has_errors(collect_issues(base(), CAPS))


def test_no_bodies_and_no_observables():
    c = base()
    c["bodies"] = []
    assert any("Kein Körper" in m for m in msgs(c, "error"))
    c = base()
    c["observables"] = []
    assert any("Keine Auswertung" in m for m in msgs(c, "error"))


def test_overlap_is_error_and_close_gap_warns():
    c = base()
    b2 = copy.deepcopy(c["bodies"][0])
    b2.update(id="b2", label="B", position=[30.0, 0, 0])
    c["bodies"].append(b2)
    assert any("überlappen" in m for m in msgs(c, "error"))
    c["bodies"][1]["position"] = [41.0, 0, 0]  # Spalt 1 nm < Elementkante 2,6 nm
    assert not any("überlappen" in m for m in msgs(c, "error"))
    assert any("Spalt" in m for m in msgs(c, "warning"))


def test_curved_with_cube_is_error():
    c = base()
    c["bodies"][0]["geometry"] = {"type": "cube", "params": {}}
    c["formulation"]["type"] = "curved"
    assert any("gekrümmte Variante" in m for m in msgs(c, "error"))


def test_chiral_host_needs_circular():
    c = base()
    c["host"]["chi"] = 0.02
    assert any("zirkular" in m.lower() for m in msgs(c, "error"))
    c["excitation"]["params"]["polarization"] = "circ_plus"
    assert not any("zirkular" in m.lower() for m in msgs(c, "error"))


def test_material_range_error():
    c = base()
    c["excitation"]["params"]["wavelength"] = 150.0
    assert any("Daten gelten nur" in m for m in msgs(c, "error"))


def test_mesh_vs_wavelength_warning():
    c = base()
    c["bodies"][0]["geometry"]["params"] = {"radius": 400.0, "n": 4}
    c["excitation"]["params"]["wavelength"] = 500.0
    assert any("verfeinern" in m for m in msgs(c, "warning"))


def test_resonance_window_for_cube_uses_eps_lookup():
    c = base()
    c["bodies"][0]["geometry"] = {"type": "cube", "params": {}}
    look = lambda i, lam: complex(-2.0, 0.5)  # noqa: E731  Kontrast −2/1,77 ≈ −1,1 liegt im Fenster
    assert any("Resonanzfenster" in m for m in msgs(c, "warning", eps_lookup=look))
    look2 = lambda i, lam: complex(-20.0, 1.0)  # noqa: E731
    assert not any("Resonanzfenster" in m for m in msgs(c, "warning", eps_lookup=look2))


def test_memory_error_when_exceeding_ram():
    c = base()
    c["bodies"][0]["geometry"]["params"] = {"radius": 20.0, "n": 40}
    c["formulation"]["type"] = "curved"
    small = {**CAPS, "memory_gb": 1.0}
    assert any("Arbeitsspeicher" in m for m in msgs(c, "error", caps=small))


def test_unavailable_plugin_is_error():
    c = base()
    c["formulation"]["type"] = "curved"
    nocurved = {**CAPS, "features": {}}
    assert any("nicht verfügbar" in m for m in msgs(c, "error", caps=nocurved))


def test_unknown_plugin_message():
    c = base()
    c["excitation"]["type"] = "xyz"
    assert any("unbekanntes Plugin" in m for m in msgs(c, "error"))


def test_cost_scales_and_curved_costs_more():
    c = base()
    e1 = estimate(resolve(c), 1)
    c["bodies"][0]["geometry"]["params"]["n"] = 16
    e2 = estimate(resolve(c), 1)
    assert e2["memory_mb"] > 3 * e1["memory_mb"] and e2["total_s"] > e1["total_s"]
    c["formulation"]["type"] = "curved"
    assert estimate(resolve(c), 1)["memory_mb"] > e2["memory_mb"]
    assert speedup(8) > speedup(1) == 1.0
    # Referenzwerte der Bibliotheksdoku: konstant 1 280 Elemente ≈ 58 MB
    c = base()
    assert 40 < estimate(resolve(c), 1)["memory_mb"] < 80


def test_spectrum_validation():
    c = base()
    c["observables"] = [{"type": "spectrum", "params": {"lam_min": 600, "lam_max": 500}}]
    assert any("größer sein" in m for m in msgs(c, "error"))
