"""Per-step event log: step, level, change, symbol, state, output and any SMS sent."""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class LogEntry:
    step: int
    h: Optional[float]
    dh: Optional[float]
    symbol: Optional[str]
    state: str
    output: str
    sms: List[str] = field(default_factory=list)


class EventLog:
    def __init__(self) -> None:
        self.entries: List[LogEntry] = []

    def add(self, entry: LogEntry) -> None:
        self.entries.append(entry)

    def clear(self) -> None:
        self.entries.clear()

    @property
    def input_string(self) -> List[str]:
        return [e.symbol for e in self.entries if e.symbol is not None]

    @property
    def output_string(self) -> List[str]:
        return [e.output for e in self.entries]

    def to_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps([asdict(e) for e in self.entries], indent=2), encoding="utf-8"
        )

    def to_csv(self, path: str | Path) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["step", "h", "dh", "symbol", "state", "output", "sms"])
            for e in self.entries:
                writer.writerow([e.step, e.h, e.dh, e.symbol, e.state, e.output, " | ".join(e.sms)])
