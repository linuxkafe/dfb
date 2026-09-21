"""Bridge between Giant Fiber circuit and Ollama payload construction."""

from dataclasses import dataclass
from typing import Optional

from .giant_fiber import GiantFiberEscapeCircuit


@dataclass
class OllamaPayload:
    temperature: float
    num_predict: int
    system_addendum: str = ""


class CoprocessorBridge:
    """
    Middleware that feeds user messages into the Giant Fiber circuit and
    returns adjusted Ollama parameters and system prompt addendum.
    """

    def __init__(self, circuit: Optional[GiantFiberEscapeCircuit] = None):
        self.circuit = circuit or GiantFiberEscapeCircuit()

    def process(
        self, user_message: str, explicit_feedback: Optional[str] = None
    ) -> OllamaPayload:
        potential = self.circuit.update(user_message, explicit_feedback)
        escape = self.circuit.should_escape()

        if escape:
            # Escape mode: deterministic, short, direct
            payload = OllamaPayload(
                temperature=0.1,
                num_predict=80,
                system_addendum=(
                    "[ESTADO INTERNO: CIRCUITO DE FUGA DISPARADO - O utilizador está num loop de "
                    "frustração/insistência. Aborta explicações longas. Apresenta apenas a solução "
                    "direta em 1-2 tópicos ou pergunta sucintamente se prefere tentar outra abordagem.]"
                ),
            )
        else:
            # Normal mode
            payload = OllamaPayload(
                temperature=0.6,
                num_predict=256,
                system_addendum="",
            )

        return payload

    def reset_escape(self) -> None:
        """Call after handling an escape response."""
        self.circuit.reset_refractory()

    def get_status(self) -> dict:
        return {
            **self.circuit.get_state(),
            "escape_active": self.circuit.should_escape(),
        }