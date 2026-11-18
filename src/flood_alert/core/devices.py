"""Simulated output devices (Tables 2, 3a and 3b).

lambda gives an output code; the driver turns it into the on/off settings of
each device. SMS messages are sent only when the output code changes, as the
proposal states under Table 3b.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class SmsMessage:
    channel: str  # "sms_team" or "sms_public"
    text: str


@dataclass
class DeviceState:
    output: str
    settings: Dict[str, str]
    sms_sent: List[SmsMessage] = field(default_factory=list)


class DeviceDriver:
    def __init__(self, devices: List[str], outputs: Dict[str, Dict[str, Optional[str]]]) -> None:
        self.devices = devices
        self.outputs = outputs
        self._last_output: Optional[str] = None

    @classmethod
    def from_config(cls, cfg: dict) -> "DeviceDriver":
        return cls(cfg["devices"], cfg["outputs"])

    def reset(self) -> None:
        self._last_output = None

    def apply(self, output: str, h: Optional[float], rate: Optional[float]) -> DeviceState:
        spec = self.outputs[output]
        settings: Dict[str, str] = {}
        for device in self.devices:
            value = spec.get(device)
            if device in ("sms_team", "sms_public"):
                settings[device] = "ON" if value else "OFF"
            else:
                settings[device] = value or "OFF"

        sms: List[SmsMessage] = []
        if output != self._last_output:
            for channel in ("sms_team", "sms_public"):
                template = spec.get(channel)
                if template:
                    sms.append(SmsMessage(channel, _fill(template, h, rate)))
        self._last_output = output
        return DeviceState(output=output, settings=settings, sms_sent=sms)


def _fill(template: str, h: Optional[float], rate: Optional[float]) -> str:
    return template.format(
        h="--" if h is None else f"{h:.2f}",
        r="--" if rate is None else f"{rate:.2f}",
    )
