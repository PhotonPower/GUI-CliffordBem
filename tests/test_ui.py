"""UI-Tests mit Streamlits AppTest: jede Seite rendert, zentrale Interaktionen wirken."""

import json
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parent.parent
PAGES = ["home", "model", "excitation", "observables", "run", "results", "runs", "help"]


def page(mod: str, cfg: dict | None = None) -> AppTest:
    code = f"from cbgui.ui import state\nstate.init()\nfrom cbgui.ui.pages import {mod}\n{mod}.render()\n"
    at = AppTest.from_string(code, default_timeout=120)
    at.run()
    if cfg is not None:
        at.session_state["cfg"] = cfg
        at.run()
    return at


def by_label(widgets, label):
    return [w for w in widgets if w.label.startswith(label)]


@pytest.mark.parametrize("mod", PAGES)
def test_page_renders(mod):
    at = page(mod)
    assert not at.exception, [e.value for e in at.exception]


def test_main_app_loads():
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=120)
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_edit_radius_updates_config():
    at = page("model")
    by_label(at.number_input, "Radius")[0].set_value(35.0).run()
    assert at.session_state["cfg"]["bodies"][0]["geometry"]["params"]["radius"] == 35.0


def test_switch_to_cube_takes_cube_defaults_and_curved_errors():
    at = page("model")
    by_label(at.selectbox, "Form")[0].select("cube").run()
    g = at.session_state["cfg"]["bodies"][0]["geometry"]
    assert g["type"] == "cube" and g["params"]["n"] == 4  # nicht der n-Wert der Kugel
    by_label(at.selectbox, "Formulierung")[0].select("curved").run()
    assert any("gekrümmte Variante" in e.value for e in at.error)


def test_dimer_assistant():
    at = page("model")
    next(b for b in at.button if b.label == "Dimer anlegen").click().run()
    bodies = at.session_state["cfg"]["bodies"]
    assert [b["label"] for b in bodies] == ["Kugel A", "Kugel B"]
    assert bodies[0]["position"][0] == -bodies[1]["position"][0] != 0


def test_observable_toggle():
    at = page("observables")
    cb = next(c for c in at.checkbox if "spektrum" in c.label)
    cb.check().run()
    assert "spectrum" in [o["type"] for o in at.session_state["cfg"]["observables"]]


def test_start_button_blocked_with_errors():
    c = json.loads((ROOT / "cbgui" / "templates" / "01_goldkugel_spektrum.json").read_text())
    c.pop("_title"), c.pop("_text")
    c["observables"] = []
    at = page("run", c)
    btn = next(b for b in at.button if "Lauf starten" in b.label)
    assert btn.disabled
