"""Rauchtests der Streamlit-Oberflaeche per AppTest: Standard, jedes Preset, alle drei Verfahren,
Runden-/Fokusteam-Regler."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ttp_constants as C

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"


def _run(setup=None):
    at = AppTest.from_file(str(APP), default_timeout=180)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def test_default_renders_without_exception():
    at = _run()
    assert any("Traveling Tournament" in t.value for t in at.title)


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders(name):
    p = C.PRESETS[name]

    def setup(at):
        at.session_state["n_teams_slider"] = p["n_teams"]
        at.session_state["seed_slider"] = p["seed"]
        at.session_state["method_radio"] = p["method"]

    _run(setup)


@pytest.mark.parametrize("method", C.METHODS)
def test_every_method_renders_at_min_and_max_n(method):
    def small(at):
        at.session_state["n_teams_slider"] = C.N_TEAMS_MIN
        at.session_state["method_radio"] = method

    _run(small)

    def large(at):
        at.session_state["n_teams_slider"] = C.N_TEAMS_MAX
        at.session_state["method_radio"] = method

    _run(large)


def test_round_slider_resets_when_n_teams_changes():
    at = _run()
    at.session_state["round_slider"] = 2
    at.run()
    assert at.session_state["round_slider"] == 2
    at.session_state["n_teams_slider"] = 6
    at.run()
    assert not at.exception
    assert at.session_state["round_slider"] == 2 * (6 - 1)


def test_focus_team_selectable():
    at = _run()
    at.session_state["focus_team_select"] = 1
    at.run()
    assert not at.exception
