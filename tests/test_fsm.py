import copy

import pytest

from flood_alert.core import FloodController, MooreMachine
from flood_alert.data import list_scenarios, load_config, load_scenario
from flood_alert.data.loader import SCENARIO_DIR


@pytest.fixture
def cfg():
    return load_config()


def make_machine(cfg):
    tr, out = cfg["transitions"], cfg["outputs"]
    return MooreMachine(tr["states"], tr["alphabet"], tr["delta"], out["lambda"], tr["initial_state"])


# ---------------------------------------------------------------- objective (c)
def test_transition_function_is_total_and_deterministic(cfg):
    m = make_machine(cfg)
    assert len(m.states) == 9
    assert len(m.alphabet) == 7
    for q in m.states:
        assert set(m.delta[q]) == set(m.alphabet)
        for a in m.alphabet:
            assert m.delta[q][a] in m.states


def test_validate_catches_a_missing_cell(cfg):
    broken = copy.deepcopy(cfg)
    del broken["transitions"]["delta"]["Recovery"]["D"]
    with pytest.raises(ValueError, match=r"delta\(Recovery, D\) is undefined"):
        make_machine(broken)


def test_every_state_is_reachable(cfg):
    m = make_machine(cfg)
    seen, frontier = {m.initial_state}, [m.initial_state]
    while frontier:
        q = frontier.pop()
        for nxt in m.delta[q].values():
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    assert seen == set(m.states)


# ------------------------------------------------------- proposal sample run
def test_sample_run_symbol_string_gives_n_plus_1_outputs(cfg):
    m = make_machine(cfg)
    symbols = "D L0 L1 R T L1 L2 L3 L2 L1 D D".split()
    outputs = m.run(symbols)
    assert len(outputs) == len(symbols) + 1
    assert outputs == (
        "MONITOR MONITOR MONITOR ADVISE SURGE SILENT HOLD SILENT FORCED SILENT HOLD HOLD MONITOR".split()
    )


def test_sample_run_from_raw_readings():
    sc = load_scenario(SCENARIO_DIR / "sample_run.json")
    ctl = FloodController.from_config_dir()
    results = [ctl.feed_event(e) for e in sc["events"]]
    assert [r.symbol for r in results] == sc["expected_symbols"]
    assert [r.state for r in results] == sc["expected_states"]
    assert [r.output for r in results] == sc["expected_outputs"]


@pytest.mark.parametrize("path", list_scenarios(), ids=lambda p: p.stem)
def test_every_scenario_matches_its_expected_states(path):
    sc = load_scenario(path)
    ctl = FloodController.from_config_dir()
    states = [ctl.feed_event(e).state for e in sc["events"]]
    assert states == sc["expected_states"]


# ------------------------------------------------------------ device driver
def test_sms_sent_only_when_output_changes():
    ctl = FloodController.from_config_dir()
    ctl.feed_reading(14.8)
    first_prep = ctl.feed_reading(15.1)  # Normal -> Prep: ADVISE
    assert [m.channel for m in first_prep.devices.sms_sent] == ["sms_team"]
    still_prep = ctl.feed_reading(15.3)  # Prep -> Prep: no new SMS
    assert still_prep.devices.sms_sent == []


def test_surge_sms_includes_level_and_rate():
    ctl = FloodController.from_config_dir()
    ctl.feed_reading(15.0)
    r = ctl.feed_reading(15.6)
    team = next(m for m in r.devices.sms_sent if m.channel == "sms_team")
    assert "15.60" in team.text and "0.60" in team.text


def test_timer_armed_only_in_surge_and_evac():
    ctl = FloodController.from_config_dir()
    assert not ctl.feed_reading(15.0).timer_armed
    assert ctl.feed_reading(15.6).timer_armed  # Surge
    assert not ctl.fire_timer().timer_armed  # Silenced


def test_reset_returns_to_q0():
    ctl = FloodController.from_config_dir()
    ctl.feed_reading(18.5)
    r = ctl.reset()
    assert (r.state, r.output, ctl.h_prev) == ("Normal", "MONITOR", None)
    assert len(ctl.log.entries) == 1
