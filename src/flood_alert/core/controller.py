"""FloodController: the one object the UI talks to.

It wires together the classifier (sigma), the Moore machine (delta, lambda),
the device driver and the event log. The UI only needs:

    controller.feed_reading(15.6)   # a new 1-minute reading
    controller.fire_timer()         # the 30-second T event
    controller.timer_armed          # True while in Surge or Evac
    controller.reset()

Each call returns a StepResult the UI can render.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .classifier import Classifier
from .devices import DeviceDriver, DeviceState
from .event_log import EventLog, LogEntry
from .fsm import MooreMachine
from ..data.loader import load_config


@dataclass
class StepResult:
    step: int
    h: Optional[float]
    dh: Optional[float]
    symbol: Optional[str]
    previous_state: Optional[str]
    state: str
    output: str
    devices: DeviceState
    timer_armed: bool

    @property
    def changed(self) -> bool:
        return self.previous_state != self.state


class FloodController:
    def __init__(
        self,
        classifier: Classifier,
        machine: MooreMachine,
        driver: DeviceDriver,
        timer_states: List[str],
        timer_s: int = 30,
    ) -> None:
        self.classifier = classifier
        self.machine = machine
        self.driver = driver
        self.timer_states = set(timer_states)
        self.timer_s = timer_s
        self.log = EventLog()
        self.h_prev: Optional[float] = None
        self.step_no = 0
        self.reset()

    @classmethod
    def from_config_dir(cls, config_dir: str | Path | None = None) -> "FloodController":
        cfg = load_config(config_dir)
        th = cfg["thresholds"]
        tr = cfg["transitions"]
        out = cfg["outputs"]
        machine = MooreMachine(
            states=tr["states"],
            alphabet=tr["alphabet"],
            delta=tr["delta"],
            lam=out["lambda"],
            initial_state=tr["initial_state"],
        )
        return cls(
            classifier=Classifier.from_config(th),
            machine=machine,
            driver=DeviceDriver.from_config(out),
            timer_states=th["timer_states"],
            timer_s=th["timer_s"],
        )

    # ---------------------------------------------------------------- state
    @property
    def state(self) -> str:
        return self.machine.state

    @property
    def output(self) -> str:
        return self.machine.output

    @property
    def timer_armed(self) -> bool:
        """True while the machine sits in a state where T is pending (Surge, Evac)."""
        return self.machine.state in self.timer_states

    def reset(self) -> StepResult:
        self.machine.reset()
        self.driver.reset()
        self.log.clear()
        self.h_prev = None
        self.step_no = 0
        return self._record(h=None, dh=None, symbol=None, previous=None)

    # ---------------------------------------------------------------- input
    def feed_reading(self, h: float) -> StepResult:
        symbol = self.classifier.classify(h, self.h_prev)
        dh = self.classifier.delta(h, self.h_prev)
        previous = self.machine.state
        self.machine.step(symbol)
        self.h_prev = h
        self.step_no += 1
        return self._record(h=h, dh=dh, symbol=symbol, previous=previous)

    def fire_timer(self) -> StepResult:
        previous = self.machine.state
        self.machine.step("T")
        self.step_no += 1
        return self._record(h=self.h_prev, dh=None, symbol="T", previous=previous)

    def feed_event(self, event: float | str) -> StepResult:
        """Scenario helper: a number is a reading, the string "T" is the timer."""
        if isinstance(event, str):
            if event.upper() != "T":
                raise ValueError(f"Unknown scenario event {event!r}")
            return self.fire_timer()
        return self.feed_reading(float(event))

    # -------------------------------------------------------------- helpers
    def _record(self, h, dh, symbol, previous) -> StepResult:
        devices = self.driver.apply(self.machine.output, h, dh)
        self.log.add(
            LogEntry(
                step=self.step_no,
                h=h,
                dh=dh,
                symbol=symbol,
                state=self.machine.state,
                output=self.machine.output,
                sms=[f"[{m.channel}] {m.text}" for m in devices.sms_sent],
            )
        )
        return StepResult(
            step=self.step_no,
            h=h,
            dh=dh,
            symbol=symbol,
            previous_state=previous,
            state=self.machine.state,
            output=self.machine.output,
            devices=devices,
            timer_armed=self.timer_armed,
        )
