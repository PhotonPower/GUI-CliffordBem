import json
import time
from pathlib import Path

import pytest

from cbgui import bridge, store
from cbgui.registry import load_plugins


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    """Jeder Test bekommt einen eigenen Datenordner."""
    monkeypatch.setenv("CBGUI_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("CBGUI_RUNS_DIR", raising=False)
    load_plugins()


@pytest.fixture(scope="session")
def lib_caps():
    caps = bridge.capabilities()
    if caps is None:
        pytest.skip("keine CliffordBem-Bibliothek erreichbar (CBGUI_WORKER_PYTHONPATH setzen)")
    return caps


@pytest.fixture
def run_cfg(lib_caps):
    """Funktion: Konfiguration im Worker rechnen, (Laufverzeichnis, Summary) zurückgeben."""

    def run(cfg: dict, timeout: float = 240.0):
        rd = bridge.start_run(cfg)
        t0 = time.time()
        while time.time() - t0 < timeout:
            st = store.live_status(rd)
            if st.get("state") in store.FINAL:
                break
            time.sleep(0.5)
        st = store.live_status(rd)
        assert st.get("state") == "done", st.get("message", "") + st.get("traceback", "")[-500:]
        return Path(rd), store.load_summary(rd)

    return run


def template_cfg(name: str) -> dict:
    p = Path(__file__).resolve().parent.parent / "cbgui" / "templates" / name
    d = json.loads(p.read_text(encoding="utf-8"))
    d.pop("_title", None)
    d.pop("_text", None)
    return d
