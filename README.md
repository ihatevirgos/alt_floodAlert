# alt_floodAlert

**Flood Alert Controller and Protocol Simulation Using Moore Machine Finite Automata for Rate-of-Change Escalation and De-escalation at a Single Monitoring Point**

COSC 302 – Automata and Language Theory · BSCS 3-4, Group 3 · Polytechnic University of the Philippines – Sta. Mesa
Bantog, Salahadin I. · Bobiles, Neriah Phoebe M. · Calderon, Mathew A. · Coritao, John Brian Z.
Instructor: Prof. Ria A. Sagum

A desktop simulator of a flood-response controller for one river gauge. Each water-level reading (one per simulated minute) is translated into an input symbol, which drives a 9-state Moore machine. Each state outputs a fixed response protocol: display, beacon, siren, voice and SMS.

## Quick start

```bash
git clone https://github.com/ihatevirgos/alt_floodAlert.git
cd alt_floodAlert
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

python main.py          # run the simulator
python -m pytest        # run the tests
```

## The machine

M = (Q, Σ, Δ, δ, λ, q₀)

| | |
|---|---|
| Q | Normal, Prep, PrepClear, Surge, Evac, Silenced, Forced, Recovery, Clearing |
| Σ | L0, L1, L2, L3, R, D, T |
| Δ | MONITOR, ADVISE, SURGE, ALARM, SILENT, FORCED, HOLD |
| δ | `config/transitions.json` (Table 6, all 63 cells written out) |
| λ | `config/outputs.json` (Tables 3a, 3b, 4) |
| q₀ | Normal |

**Input translator σ(h, Δh)**, priority L3 > R > L2 > L1:

| Symbol | Condition |
|---|---|
| L3 | h ≥ 18 m |
| R | 15 ≤ h < 18 m and Δh ≥ 0.5 m |
| L2 | 16 ≤ h < 18 m |
| L1 | 15 ≤ h < 16 m |
| L0 | h < 15 m and rising |
| D | h < 15 m and steady or falling (also the first reading below 15 m) |
| T | 30 s after entering Surge or Evac |

## Project layout

```
config/            Data layer: thresholds, δ table, λ + device specs (JSON)
scenarios/         Preset flood scenarios with expected states
src/flood_alert/
  core/            Application layer, no GUI code
    classifier.py    σ: reading -> symbol
    fsm.py           generic Moore machine + totality/determinism check
    devices.py       λ -> device settings; SMS only when λ changes
    event_log.py     per-step log, CSV/JSON export
    controller.py    FloodController: the one class the UI talks to
  data/loader.py   reads config/ and scenarios/
  ui/              Presentation layer (PySide6)
tests/             pytest: classifier boundaries, δ totality, sample run, scenarios
tools/make_jflap.py   regenerates docs/jflap/flood_alert_moore.jff from the δ table
docs/              proposal, JFLAP file, diagrams
main.py            app entry point
```

### Using the core from the UI

```python
from flood_alert.core import FloodController

ctl = FloodController.from_config_dir()
r = ctl.feed_reading(15.6)    # -> StepResult
r.symbol, r.state, r.output   # 'R', 'Surge', 'SURGE'
r.devices.settings            # {'display': 'RAPID RISE: EVACUATE NOW', 'siren': 'ON, continuous', ...}
r.devices.sms_sent            # SMS messages sent on this step
r.timer_armed                 # True -> start the 30 s countdown, then call ctl.fire_timer()
```

## JFLAP verification

`docs/jflap/flood_alert_moore.jff` is generated from `config/transitions.json`, so JFLAP and the code always check the same table. Regenerate it with `python tools/make_jflap.py` after any change to δ.

| Symbol | L0 | L1 | L2 | L3 | R | D | T |
|---|---|---|---|---|---|---|---|
| JFLAP | a | b | c | d | r | s | t |

| Output | MONITOR | ADVISE | SURGE | ALARM | SILENT | FORCED | HOLD |
|---|---|---|---|---|---|---|---|
| JFLAP | M | A | S | L | Q | F | H |

Sample run from the proposal: input `sabrtbcdcbss` gives output `MMMASQHQFQHHM`.

## Team workflow

| Member | Role | Main folders |
|---|---|---|
| Bantog | Project & documentation lead | `README.md`, `docs/` |
| Bobiles | System designer | `config/`, `docs/jflap/`, diagrams |
| Calderon | Frontend | `src/flood_alert/ui/`, `main.py` |
| Coritao | Backend | `src/flood_alert/core/`, `data/`, `tests/` |

1. `main` holds demo-ready code only. Day-to-day work goes to `dev`.
2. Make a branch for each task from `dev`: `git checkout dev && git pull && git checkout -b feature/<task>`.
3. Commit, push, then open a Pull Request **into `dev`**. Another member reviews it before merging.
4. The tests run automatically on every PR. Don't merge a red one.
5. Merge `dev` into `main` before each demo or checkpoint.

If you change `config/transitions.json`, update the expected states in `scenarios/` and re-run `python tools/make_jflap.py`.
