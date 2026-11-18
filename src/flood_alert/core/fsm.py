"""A generic Moore machine M = (Q, Sigma, Delta, delta, lambda, q0).

This class knows nothing about floods; the flood-specific tables come from
config/transitions.json and config/outputs.json.
"""

from __future__ import annotations

from typing import Dict, Iterable, List


class MooreMachine:
    def __init__(
        self,
        states: Iterable[str],
        alphabet: Iterable[str],
        delta: Dict[str, Dict[str, str]],
        lam: Dict[str, str],
        initial_state: str,
    ) -> None:
        self.states = list(states)
        self.alphabet = list(alphabet)
        self.delta = delta
        self.lam = lam
        self.initial_state = initial_state
        self.validate()
        self.state = initial_state

    # ------------------------------------------------------------------ checks
    def validate(self) -> None:
        """Raise ValueError unless delta is total and deterministic and lambda covers Q.

        This is the code-side counterpart of specific objective (c): every
        (state, symbol) pair must have exactly one next state.
        """
        problems: List[str] = []
        if self.initial_state not in self.states:
            problems.append(f"initial state {self.initial_state!r} is not in Q")
        for q in self.states:
            row = self.delta.get(q)
            if row is None:
                problems.append(f"no transitions for state {q!r}")
                continue
            for a in self.alphabet:
                if a not in row:
                    problems.append(f"delta({q}, {a}) is undefined")
                elif row[a] not in self.states:
                    problems.append(f"delta({q}, {a}) = {row[a]!r} is not in Q")
            for a in row:
                if a not in self.alphabet:
                    problems.append(f"delta({q}, {a}) uses a symbol not in Sigma")
            if q not in self.lam:
                problems.append(f"lambda({q}) is undefined")
        for q in self.delta:
            if q not in self.states:
                problems.append(f"transitions given for unknown state {q!r}")
        if problems:
            raise ValueError("Invalid Moore machine:\n  " + "\n  ".join(problems))

    # --------------------------------------------------------------- running
    @property
    def output(self) -> str:
        return self.lam[self.state]

    def reset(self) -> None:
        self.state = self.initial_state

    def step(self, symbol: str) -> str:
        if symbol not in self.alphabet:
            raise ValueError(f"{symbol!r} is not in the input alphabet {self.alphabet}")
        self.state = self.delta[self.state][symbol]
        return self.state

    def run(self, symbols: Iterable[str]) -> List[str]:
        """Run from q0 and return the Moore output string.

        For n input symbols this returns n + 1 outputs: lambda(q0) first,
        then one output per state entered.
        """
        self.reset()
        outputs = [self.output]
        for s in symbols:
            self.step(s)
            outputs.append(self.output)
        return outputs
