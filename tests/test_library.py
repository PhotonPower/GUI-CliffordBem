"""Tests mit echter Bibliothek (Marker ``library``). Kleine Netze, zusammen etwa eine Minute."""

import copy

import numpy as np
import pytest

from cbgui import bridge, store
from cbgui.config import default_config
from cbgui.reference.mie import mie_sphere

from .conftest import template_cfg

pytestmark = pytest.mark.library


def sphere_cfg(n=4, form="flat", obs=None, radius=20.0):
    c = default_config()
    c["bodies"][0]["geometry"]["params"] = {"radius": radius, "n": n}
    c["formulation"]["type"] = form
    c["observables"] = obs or [{"type": "extinction", "params": {}}]
    return c


def test_capabilities(lib_caps):
    assert lib_caps["features"]["curved"] and lib_caps["features"]["near_field"]
    assert lib_caps["materials"]["Au"][0] < 200 and lib_caps["threads"] >= 1


def test_polarization_basis_matches_library(lib_caps):
    import subprocess

    from cbgui.plugins.excitations import polarization_basis

    rng = np.random.default_rng(3)
    dirs = [(0, 0, 1), (0, 0, -1), (1, 0, 0), (0, 1, 0), (1, 1, 1)] + [tuple(rng.normal(size=3)) for _ in range(5)]
    code = ("import json,sys,numpy as np,cliffordbem as cb\n"
            "ds=json.loads(sys.stdin.read()); out=[]\n"
            "for d in ds:\n"
            "    d=np.array(d,float); d/=np.linalg.norm(d); u,v=cb.polarization_basis(d); out.append([u.tolist(),v.tolist()])\n"
            "print(json.dumps(out))")
    import json

    r = subprocess.run([bridge.worker_python(), "-c", code], input=json.dumps(dirs), capture_output=True, text=True, env=bridge.worker_env())
    assert r.returncode == 0, r.stderr
    for d, (u, v) in zip(dirs, json.loads(r.stdout.strip().splitlines()[-1]), strict=True):
        u2, v2 = polarization_basis(d)
        assert np.allclose(u, u2) and np.allclose(v, v2)


def test_sphere_against_mie_flat_and_curved(run_cfg):
    ref = mie_sphere(complex(-4.546130398428235, 2.457669093823717), 1.33, 20.0, 530.0)["sigma_ext_nm2"][0]
    _, s_flat = run_cfg(sphere_cfg(8, "flat"))
    _, s_curved = run_cfg(sphere_cfg(3, "curved"))
    val = lambda s: float(s["observables"][0]["metrics"]["σ_ext"].replace(" ", "").replace("nm²", ""))  # noqa: E731
    assert abs(val(s_flat) / ref - 1) < 0.02  # O(h²), n = 8: etwa 1,2 %
    assert abs(val(s_curved) / ref - 1) < 0.003  # O(h⁴), n = 3: etwa 0,2 %


def test_all_observables_and_force_normalization(run_cfg):
    obs = [{"type": "extinction", "params": {}}, {"type": "nearfield", "params": {"nu": 21, "nv": 15}},
           {"type": "forces", "params": {"intensity": 1.0}}, {"type": "spectrum", "params": {"lam_min": 500, "lam_max": 560, "n_points": 3}}]
    rd, s = run_cfg(sphere_cfg(4, obs=obs))
    data = store.load_results(rd)
    assert [o["id"] for o in s["observables"]] == ["extinction", "nearfield", "forces", "spectrum"]  # Reihenfolge wie konfiguriert
    sig = data[0]["sigma_nm2"]
    # Strahlungsdruck F = σ_pr · n · I / c; σ_pr ≤ σ_ext, bei Gold in Wasser ≈ σ_ext (kleine Teilchen)
    f_expected = sig * 1e-6 * 1.33 * 1e-3 / 2.99792458e8 * 1e12
    fz = float(data[2]["total_pN"][2])
    assert 0.8 * f_expected < fz <= 1.02 * f_expected
    assert np.nanmax(data[1]["enhancement"]) > 5 and data[1]["invalid"].any()
    assert np.allclose(data[2]["force_pN"][:, :2], 0, atol=1e-6 * fz)  # Querkräfte verschwinden
    far = float(data[2]["farfield_total_pN"][2])
    assert abs(fz / far - 1) < 0.03  # Spannungstensor gegen Impulsbilanz
    assert data[3]["sigma_nm2"].shape == (3,) and abs(data[3]["sigma_nm2"][1] - sig) < 1e-6 * sig  # 530 nm = Extinktion


def test_spectrum_cd_chiral_and_orientation(run_cfg):
    c = sphere_cfg(3, obs=[{"type": "spectrum", "params": {"lam_min": 500, "lam_max": 600, "n_points": 2, "pol": "circular", "orient": 1}}])
    c["bodies"][0]["material"] = {"type": "constant_n", "params": {"n": 1.5, "k": 0.0}}
    c["bodies"][0]["geometry"]["params"]["radius"] = 100.0
    c["bodies"][0]["chi"] = 0.02
    rd, _ = run_cfg(c)
    d = store.load_results(rd)[0]
    assert np.all(np.abs(d["cd_nm2"]) > 1.0)  # chiral: CD ≠ 0
    c["bodies"][0]["chi"] = 0.0
    rd, _ = run_cfg(c)
    assert np.all(np.abs(store.load_results(rd)[0]["cd_nm2"]) < 1e-3 * store.load_results(rd)[0]["sigma_nm2"])  # achiral: CD ≈ 0
    # Orientierungsmittelung einer Kugel = Einzelrichtung
    c = sphere_cfg(3, obs=[{"type": "spectrum", "params": {"lam_min": 530, "lam_max": 560, "n_points": 2, "pol": "unpolarized", "orient": 6}}])
    rd, _ = run_cfg(c)
    avg = store.load_results(rd)[0]["sigma_nm2"][0]
    rd, _ = run_cfg(sphere_cfg(3))
    assert abs(avg / store.load_results(rd)[0]["sigma_nm2"] - 1) < 5e-3


def test_dimer_force_is_attractive(run_cfg):
    c = template_cfg("03_golddimer_nahfeld.json")
    for b in c["bodies"]:
        b["geometry"]["params"]["n"] = 4
    c["observables"] = [{"type": "forces", "params": {}}]
    rd, _ = run_cfg(c)
    F = store.load_results(rd)[0]["force_pN"]
    assert F[0, 0] > 0 > F[1, 0]  # Kugeln ziehen sich an (A links, B rechts)


def test_gmsh_curved_beats_flat(run_cfg, lib_caps):
    import os

    msh = os.path.join(os.path.dirname(lib_caps["data_dir"]), "meshes", "sphere_r1_order2_gmsh41.msh")
    if not os.path.isfile(msh):
        pytest.skip("Testnetz nicht gefunden")
    c = default_config()
    c["bodies"][0]["geometry"] = {"type": "gmsh", "params": {"file": msh, "group": 1, "file_unit": "µm", "center": True}}
    c["bodies"][0]["material"] = {"type": "constant_n", "params": {"n": 1.5, "k": 0.0}}
    c["host"]["n"] = 1.0
    c["excitation"]["params"]["wavelength"] = 1500.0
    c["observables"] = [{"type": "extinction", "params": {}}]
    ref = mie_sphere(2.25 + 0j, 1.0, 1000.0, 1500.0)["sigma_ext_nm2"][0]
    res = {}
    for form in ("flat", "curved"):
        c["formulation"]["type"] = form
        rd, _ = run_cfg(copy.deepcopy(c))
        res[form] = store.load_results(rd)[0]["sigma_nm2"]
    assert abs(res["curved"] / ref - 1) < 0.005 and abs(res["flat"] / ref - 1) > 0.05


def test_overlap_rejected_by_worker(lib_caps):
    c = sphere_cfg(3)
    b2 = copy.deepcopy(c["bodies"][0])
    b2.update(id="b2", label="B2", position=[10.0, 0, 0])
    c["bodies"].append(b2)
    import time

    rd = bridge.start_run(c)
    for _ in range(60):
        st = store.live_status(rd)
        if st["state"] in store.FINAL:
            break
        time.sleep(0.5)
    assert st["state"] == "error" and "überlappen" in st["message"]


def test_inspect_and_material_eps(lib_caps):
    r = bridge.query("material_eps", {"type": "tabulated", "params": {"name": "Au"}, "lams": [530.0]})
    assert r["eps_re"][0] == pytest.approx(-4.546, abs=1e-3) and r["eps_im"][0] > 0


@pytest.mark.parametrize("name", ["01_goldkugel_spektrum.json", "02_goldkugel_gekruemmt.json", "03_golddimer_nahfeld.json",
                                  "04_chirale_kugel_cd.json", "05_silberwuerfel_spektrum.json"])
def test_templates_run_reduced(run_cfg, name):
    c = template_cfg(name)
    for b in c["bodies"]:
        p = b["geometry"]["params"]
        if "n" in p:
            p["n"] = 2 if (b["geometry"]["type"] == "cube" or c["formulation"]["type"] == "curved") else 4
    for o in c["observables"]:
        if o["type"] == "spectrum":
            o["params"]["n_points"] = 3
        if o["type"] == "nearfield":
            o["params"].update({"nu": 15, "nv": 11})
    rd, s = run_cfg(c)
    assert s["not_converged"] == 0 and (rd / "results.npz").exists() and (rd / "report.txt").exists()
    from cbgui.registry import OBSERVABLES

    data = store.load_results(rd)
    for i, o in enumerate(c["observables"]):
        O = OBSERVABLES.get(o["type"])()
        figs = O.figures(data[i], {"cfg": c}, {f.key: f.default for f in O.view_fields})
        assert isinstance(figs, list) and O.summary(data[i])
