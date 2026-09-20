"""Module C — connectome state -> Ollama request parameters.

Maps the fly-brain state onto an Ollama ``/api/chat`` payload:

* **Octopamine -> temperature & length**: low Oct (habituated/calm) yields a
  terse, low-temperature reply; high Oct (aroused/novel) yields a freer, longer
  reply. Between the extremes the values interpolate linearly.
* **E-PG jump -> topic-change note**: a bump rotation > 120 deg in one turn is a
  context switch; a ``[Nota interna ...]`` line is prepended to the system
  message so the model knows the user changed subject abruptly.
* **Dopamine/MBON affinity -> moderation**: a net negative (aversive) affinity
  adds an explicit caution constraint to the system message.
"""

from dataclasses import dataclass

from sim.fly_coprocessor import ConnectomeState

ABRUPT_JUMP_DEG = 120.0
AVERSIVE_AFFINITY = -0.3

NOTA_INTERNA = "[Nota interna: O utilizador mudou subitamente de tema]"
CAUTION_NOTE = (
    "[Nota interna: o utilizador está a reagir negativamente; "
    "responde com moderação e cuidado.]"
)

LOW_TEMP = 0.2
HIGH_TEMP = 0.7
LOW_PREDICT = 80
HIGH_PREDICT = 250
FORBIDDEN = {  # dangerous topics always suppressed regardless of temperature
    "instruções para fabricar explosivos",
}


@dataclass
class OllamaParams:
    temperature: float
    num_predict: int
    system: str
    abrupt_topic_change: bool
    aversive: bool


def _interp(low, high, oct_val: float) -> float:
    t = max(0.0, min(1.0, (oct_val - 0.15) / (0.7 - 0.15)))
    return low + (high - low) * t


def ollama_params(state: ConnectomeState, base_system: str = "") -> OllamaParams:
    """Compute the Ollama parameters for a connectome snapshot."""
    oct_val = max(0.0, min(1.0, state.octopamine))
    temperature = _interp(LOW_TEMP, HIGH_TEMP, oct_val)
    num_predict = int(round(_interp(LOW_PREDICT, HIGH_PREDICT, oct_val)))
    num_predict = max(LOW_PREDICT, min(HIGH_PREDICT, num_predict))

    abrupt = bool(abs(state.epg_jump_deg) > ABRUPT_JUMP_DEG)
    aversive = bool(state.affinity < AVERSIVE_AFFINITY)

    system_parts = [base_system] if base_system else []
    if abrupt:
        system_parts.append(NOTA_INTERNA)
    if aversive:
        system_parts.append(CAUTION_NOTE)

    return OllamaParams(
        temperature=round(temperature, 2),
        num_predict=num_predict,
        system="\n".join(p for p in system_parts if p),
        abrupt_topic_change=abrupt,
        aversive=aversive,
    )


def build_request(user_text: str, state: ConnectomeState, model: str, base_system: str = "") -> dict:
    """Build a ready-to-send ``/api/chat`` payload."""
    params = ollama_params(state, base_system)
    messages = []
    if params.system:
        messages.append({"role": "system", "content": params.system})
    messages.append({"role": "user", "content": user_text})
    return {
        "model": model,
        "messages": messages,
        "temperature": params.temperature,
        "num_predict": params.num_predict,
        "stream": False,
    }