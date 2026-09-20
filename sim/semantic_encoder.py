"""Module B — semantic encoder: text -> topic angle for the E-PG ring.

Topic/keyword hashing maps a message to a deterministic angle in 0..360 deg that
drives the E-PG bump, so a persistent topic pins the bump while a new topic
rotates it. To make *similar* messages land on *nearby* angles, the hash buckets
the message by its most salient keywords rather than the raw byte string.

Pre-synaptic habituation: identical or too-fast messages reduce the injected
current amplitude, so the E-PG bump and the mushroom body get a weaker drive
under repetition.
"""

import hashlib
import re
from collections import deque

import numpy as np

from sim.fly_coprocessor import circular_distance

MIN_INJECTION = 0.05
FAST_DT = 4.0  # seconds: inter-arrival below this counts as "too fast"
HAB_ANGLE_DEG = 30.0  # messages closer than this are "the same topic"

_STOPWORDS = {
    "a", "o", "e", "de", "do", "da", "em", "no", "na", "com", "para", "por",
    "um", "uma", "que", "and", "the", "of", "to", "you", "is", "in", "it",
    "i", "me", "my", "this", "that",
}


class SemanticEncoder:
    """Maps messages onto deterministic topic angles and injectable currents."""

    def __init__(self, seed: int = 42):
        self._last_angle: float | None = None
        self._last_t: float = 0.0
        self._injection: float = 1.0
        self._recent: deque = deque(maxlen=8)
        self._rng = np.random.RandomState(seed)

    # ------------------------------------------------------------------
    # Angle encoding
    # ------------------------------------------------------------------

    @staticmethod
    def _keywords(text: str) -> list[str]:
        tokens = re.findall(r"[a-zA-Z0-9áéíóúâêôãõçü]+", text.lower())
        seen = []
        for tok in tokens:
            if tok in _STOPWORDS or tok in seen:
                continue
            seen.append(tok)
        return seen[-3:]  # keep the three most recent salient keywords

    def angle_for(self, text: str) -> float:
        """Deterministic 0..360 deg angle for a message."""
        keys = self._keywords(text) or ["none"]
        digest = hashlib.sha256("|".join(keys).encode("utf-8")).digest()
        return (int.from_bytes(digest[:3], "big") % 360000) / 1000.0

    # ------------------------------------------------------------------
    # Habituation
    # ------------------------------------------------------------------

    def _update_habituation(self, delta_deg: float, dt: float) -> None:
        if self._last_angle is None:
            self._injection = 1.0
            return
        if abs(delta_deg) < HAB_ANGLE_DEG and dt <= FAST_DT:
            self._injection = max(MIN_INJECTION, self._injection * 0.55)
        else:
            self._injection = min(1.0, self._injection + 0.4 + 0.15 * abs(delta_deg) / 180.0)

    def novelty(self, delta_deg: float, dt: float) -> float:
        """Novelty in 0..1; falls under repetition, spikes on abrupt change."""
        if self._last_angle is None:
            return 1.0
        novelty = float(np.clip(abs(delta_deg) / 120.0, 0.0, 1.0))
        if abs(delta_deg) < HAB_ANGLE_DEG and dt <= FAST_DT:
            novelty *= 0.25  # repetition suppresses the novelty signal
        return novelty

    # ------------------------------------------------------------------
    # Public step
    # ------------------------------------------------------------------

    def __call__(self, text: str, t: float) -> tuple[float, float, float]:
        """Encode ``text`` -> (angle, injection_amplitude, novelty)."""
        angle = self.angle_for(text)
        dt = max(t - self._last_t, 0.0) if self._last_t is not None else 0.0
        delta = circular_distance(self._last_angle or angle, angle)
        self._update_habituation(delta, dt)
        nov = self.novelty(delta, dt)
        self._last_angle = angle
        self._last_t = t
        self._recent.append((angle, t))
        return angle, float(self._injection), nov