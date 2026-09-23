"""Giant Fiber Escape Circuit for Drosophila-inspired frustration detection."""

from collections import deque
from typing import Optional


class GiantFiberEscapeCircuit:
    """
    Biologically-inspired circuit that accumulates membrane potential based on
    user frustration signals and triggers an escape response when threshold is crossed.
    """

    def __init__(
        self,
        escape_threshold: float = 0.5,
        decay_rate: float = 0.05,
        history_size: int = 5,
    ):
        self.membrane_potential: float = 0.0
        self.escape_threshold = escape_threshold
        self.decay_rate = decay_rate
        self.habituation_history: deque[str] = deque(maxlen=history_size)
        self._refractory: bool = False
        self._call_count: int = 0

    def _lexical_overlap(self, current: str, previous: str) -> float:
        """Simple word overlap ratio between two messages."""
        if not previous:
            return 0.0
        cur_words = set(current.lower().split())
        prev_words = set(previous.lower().split())
        if not cur_words:
            return 0.0
        return len(cur_words & prev_words) / len(cur_words)

    def _punctuation_boost(self, text: str) -> float:
        boost = 0.0
        if "?" in text:
            boost += 0.1 * min(text.count("?"), 3)
        if "!" in text:
            boost += 0.1 * min(text.count("!"), 3)
        # all caps words
        caps = sum(1 for w in text.split() if w.isupper() and len(w) > 2)
        boost += 0.05 * min(caps, 3)
        return min(boost, 0.2)

    def update(
        self, user_message: str, explicit_feedback: Optional[str] = None
    ) -> float:
        """
        Update membrane potential based on the new user message.
        Returns the new potential value.
        """
        # natural decay
        self.membrane_potential = max(0.0, self.membrane_potential - self.decay_rate)

        # small base stress accumulation per turn
        self.membrane_potential += 0.1

        if self.habituation_history:
            prev = self.habituation_history[-1]
            # lexical repetition
            overlap = self._lexical_overlap(user_message, prev)
            if overlap > 0.3:
                self.membrane_potential += 0.2 + 0.1 * overlap
            # short repeated messages
            if len(user_message) < 60 and overlap > 0.2:
                self.membrane_potential += 0.1

        # frustration keywords
        frustration_words = {
            "erro",
            "falha",
            "não funciona",
            "nada",
            "erro de novo",
            "mesmo erro",
        }
        lower = user_message.lower()
        for w in frustration_words:
            if w in lower:
                self.membrane_potential += 0.3
                break

        # punctuation / caps
        self.membrane_potential += self._punctuation_boost(user_message)

        # explicit aversive feedback
        if explicit_feedback == "--":
            self.membrane_potential += 0.8

        # clamp
        self.membrane_potential = min(1.0, self.membrane_potential)

        # store
        self.habituation_history.append(user_message)
        self._call_count += 1

        return self.membrane_potential

    def should_escape(self) -> bool:
        """Return True if escape threshold reached and not in refractory period."""
        if self._refractory:
            return False
        if self._call_count < 5:
            return False
        if self.membrane_potential >= self.escape_threshold:
            self._refractory = True
            return True
        return False

    def reset_refractory(self) -> None:
        """Call after handling escape to allow future escapes."""
        self._refractory = False

    def get_state(self) -> dict:
        return {
            "membrane_potential": round(self.membrane_potential, 3),
            "threshold": self.escape_threshold,
            "refractory": self._refractory,
        }
