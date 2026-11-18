"""The input translator sigma(h, dh): turns a raw reading into one symbol of the alphabet.

Rules (Proposal No. 1, Table 5):

    L3  h >= 18 m
    R   15 m <= h < 18 m and dh >= 0.5 m        (rapid rise, by rate)
    L2  16 m <= h < 18 m
    L1  15 m <= h < 16 m
    L0  h < 15 m and h >  previous reading
    D   h < 15 m and h <= previous reading

Where definitions overlap the priority is L3 > R > L2 > L1.
The very first reading has no previous value, so only its band is used
(below 15 m it counts as D, i.e. "steady").
"""

from __future__ import annotations

from typing import Optional

# Rounding avoids float noise such as 16.4 - 15.9 = 0.49999999999999822.
_PRECISION = 6


class Classifier:
    def __init__(
        self,
        prep_level_m: float = 15.0,
        evac_level_m: float = 16.0,
        forced_level_m: float = 18.0,
        rapid_rise_m: float = 0.5,
    ) -> None:
        if not (prep_level_m < evac_level_m < forced_level_m):
            raise ValueError("Thresholds must satisfy prep < evac < forced.")
        self.prep_level_m = prep_level_m
        self.evac_level_m = evac_level_m
        self.forced_level_m = forced_level_m
        self.rapid_rise_m = rapid_rise_m

    @classmethod
    def from_config(cls, cfg: dict) -> "Classifier":
        return cls(
            prep_level_m=cfg["prep_level_m"],
            evac_level_m=cfg["evac_level_m"],
            forced_level_m=cfg["forced_level_m"],
            rapid_rise_m=cfg["rapid_rise_m"],
        )

    @staticmethod
    def delta(h: float, h_prev: Optional[float]) -> Optional[float]:
        """Rate of change in metres per reading, or None for the first reading."""
        if h_prev is None:
            return None
        return round(h - h_prev, _PRECISION)

    def classify(self, h: float, h_prev: Optional[float]) -> str:
        if h < 0:
            raise ValueError("Water level cannot be negative.")
        dh = self.delta(h, h_prev)

        if h >= self.forced_level_m:
            return "L3"
        if h >= self.prep_level_m:
            if dh is not None and dh >= self.rapid_rise_m:
                return "R"
            if h >= self.evac_level_m:
                return "L2"
            return "L1"
        # Below the prep level: only the direction matters.
        if dh is not None and dh > 0:
            return "L0"
        return "D"
