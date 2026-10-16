import json

import numpy as np
import pytest

from cbgui import store
from cbgui.reference.mie import mie_sphere


def test_mie_lossless_ext_equals_sca():
    r = mie_sphere(2.25 + 0j, 1.0, 100.0, np.array([500.0, 700.0]))
    assert np.allclose(r["q_ext"], r["q_sca"], rtol=1e-10) and np.allclose(r["q_abs"], 0, atol=1e-10)


def test_mie_rayleigh_limit():
    # kleine Kugel: Q_sca = (8/3) x⁴ |(m²−1)/(m²+2)|²
    lam, a, n, eps = 5000.0, 10.0, 1.0, 2.25 + 0j
    x = 2 * np.pi * n * a / lam
    ray = 8 / 3 * x**4 * abs((eps - 1) / (eps + 2)) ** 2
    assert mie_sphere(eps, n, a, lam)["q_sca"][0] == pytest.approx(ray, rel=2e-3)


def test_mie_gold_peak_in_water():
    eps = np.array([-4.55 + 2.46j])  # Au bei 530 nm (Johnson–Christy)
    r = mie_sphere(eps, 1.33, 20.0, 530.0)
    assert r["sigma_ext_nm2"][0] == pytest.approx(3649.6, rel=2e-3)  # gegen CliffordBem-Referenz geprüft
    assert r["q_abs"][0] > 0


def test_status_atomic_and_live_crash(tmp_path):
    d = tmp_path / "r"
    d.mkdir()
    store.write_status(d, state="solving", worker_pid=2**22 + 7)  # PID existiert nicht
    st = store.live_status(d)
    assert st["state"] == "error" and st["crashed"]
    store.write_status(d, state="done")
    assert store.live_status(d)["state"] == "done"


def test_new_run_dir_unique_and_slug():
    a, b = store.new_run_dir("Au Kugel/1"), store.new_run_dir("Au Kugel/1")
    assert a != b and "/" not in a.name[16:] and a.parent == store.runs_dir()


def test_load_results_splits_by_observable(tmp_path):
    d = tmp_path / "r"
    d.mkdir()
    (d / "config.json").write_text(json.dumps({"observables": [{"type": "a"}, {"type": "b"}]}))
    np.savez(d / "results.npz", **{"obs0__x": np.arange(3), "obs1__s": np.array("text"), "obs1__v": np.array(2.5)})
    r = store.load_results(d)
    assert list(r[0]["x"]) == [0, 1, 2] and r[1]["s"] == "text" and r[1]["v"] == 2.5


def test_delete_only_inside_runs_dir(tmp_path):
    with pytest.raises(ValueError):
        store.delete_run(tmp_path)
