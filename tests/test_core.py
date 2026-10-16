import math

import numpy as np
import pytest

from cbgui import config
from cbgui.base import Issue
from cbgui.model import resolve
from cbgui.params import Field, Schema
from cbgui.registry import EXCITATIONS, FORMULATIONS, GEOMETRIES, MATERIALS, OBSERVABLES, Plugin, Registry


def test_schema_defaults_and_errors():
    s = Schema([Field("a", "A", "float", 1.0, "nm", min=0.5, max=2.0), Field("c", "C", "choice", "x", choices=(("x", "X"), ("y", "Y")))])
    assert s.defaults() == {"a": 1.0, "c": "x"}
    assert s.errors({"a": 1.0}) == []
    assert "liegt unter" in s.errors({"a": 0.1})[0]
    assert "liegt über" in s.errors({"a": 9})[0]
    assert s.errors({"a": float("nan")})
    assert s.errors({"c": "z"})
    assert s.fill({"a": 2, "unbekannt": 1}) == {"a": 2, "c": "x"}


def test_schema_hidden_fields_are_not_checked():
    s = Schema([Field("m", "M", "bool", False), Field("w", "W", "float", 1.0, min=5.0, visible_if=lambda v: v["m"])])
    assert s.errors({"m": False}) == []
    assert s.errors({"m": True})


def test_duplicate_keys_rejected():
    with pytest.raises(ValueError):
        Schema([Field("a", "A"), Field("a", "B")])


def test_registry_rejects_duplicates_and_gates_features():
    r = Registry("test")

    class P(Plugin):
        id = "p"
        requires = ("curved",)
        min_version = "0.47"

    r.register(P)

    class Q(Plugin):
        id = "p"

    with pytest.raises(ValueError):
        r.register(Q)
    assert P.unavailable_reason(None) is None
    assert "curved" in P.unavailable_reason({"version": "0.63", "features": {}})
    assert "0.47" in P.unavailable_reason({"version": "0.40", "features": {"curved": True}})
    assert P.unavailable_reason({"version": "0.63.0", "features": {"curved": True}}) is None
    assert Issue("info", "x").level == "info"
    with pytest.raises(ValueError):
        Issue("fatal", "x")


@pytest.mark.parametrize("reg", [GEOMETRIES, MATERIALS, EXCITATIONS, FORMULATIONS, OBSERVABLES])
def test_every_plugin_has_valid_defaults(reg):
    assert reg.ids()
    for P in reg.all():
        assert P.id and P.label
        assert P.schema().errors(P.schema().defaults()) == [], P.id
        for f in getattr(P, "view_fields", ()):
            assert f.key


def test_geometry_plugins_basic_contract():
    for G in GEOMETRIES.all():
        if G.id == "gmsh":
            continue
        g, p = G(), G.schema().defaults()
        v, f = g.preview(p)
        assert v.ndim == 2 and v.shape[1] == 3 and f.max() < len(v)
        assert g.n_elements(p) > 0 and g.element_size(p) > 0
        assert g.reference_length(p) > 0 and g.bounding_radius(p) >= g.reference_length(p)
        if g.resolution_key:
            assert set(g.resolution_presets) <= {"flat", "curved"}


def test_sphere_and_cube_counts():
    s = GEOMETRIES.get("sphere")()
    assert s.n_elements({"radius": 20, "n": 4}) == 320
    c = GEOMETRIES.get("cube")()
    assert c.n_elements({"edge": 40, "mesh": "uniform", "n": 3}) == 108
    assert c.n_elements({"edge": 40, "mesh": "graded", "n": 3}) == 768
    assert c.has_sharp_edges({})


def test_preview_sphere_is_closed_and_round():
    v, f = GEOMETRIES.get("sphere")().preview({"radius": 10.0, "n": 8})
    assert np.allclose(np.linalg.norm(v, axis=1), 10.0)
    assert len(f) == 1280


def test_materials_numpy_and_sign_convention():
    eps = MATERIALS.get("constant_n")().eps_numpy({"n": 1.5, "k": 0.1}, 500)
    assert eps == pytest.approx(complex(1.5, 0.1) ** 2) and eps.imag > 0
    d = MATERIALS.get("drude")().eps_numpy({"eps_inf": 9.84, "hbar_wp": 9.03, "hbar_gamma": 0.07}, 530.0)
    assert d.real < 0 and d.imag > 0
    assert MATERIALS.get("tabulated")().eps_numpy({"name": "Au"}, 500) is None  # braucht die Bibliothek


def test_config_roundtrip_and_migration():
    c = config.default_config()
    assert config.loads_config(config.to_json(c))["schema_version"] == config.SCHEMA_VERSION
    old = {"schema_version": 0, "bodies": [{"geometry": {"type": "sphere", "params": {}}}]}
    m = config.migrate(old)
    assert m["bodies"][0]["id"] and m["solver"]["tol"] > 0 and m["observables"]
    with pytest.raises(ValueError):
        config.migrate({"schema_version": 999})


def test_resolve_unit_and_counts():
    c = config.default_config()
    c["bodies"][0]["geometry"]["params"] = {"radius": 25.0, "n": 4}
    m = resolve(c)
    assert m.unit_nm == 25.0 and m.n_elements() == 320 and m.unknowns() == 2560
    c["formulation"]["type"] = "curved"
    assert resolve(c).unknowns() == 320 * 24


def test_resolve_unknown_plugin_raises():
    c = config.default_config()
    c["bodies"][0]["geometry"]["type"] = "gibtsnicht"
    with pytest.raises(KeyError):
        resolve(c)


def test_excitation_direction_and_polarization_are_orthonormal():
    E = EXCITATIONS.get("plane_wave")()
    p = E.schema().fill({"direction": "custom", "theta": 40, "phi": 70, "polarization": "linear", "psi": 30})
    d, e = E.direction(p), E.polarization_vector(p)
    assert math.isclose(np.linalg.norm(d), 1.0) and abs(d @ e) < 1e-12 and math.isclose(np.linalg.norm(e), 1.0)
