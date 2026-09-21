"""Test for Giant Fiber escape circuit and bridge behaviour."""

import pytest

from src.dfb.coprocessor.giant_fiber import GiantFiberEscapeCircuit
from src.dfb.coprocessor.bridge import CoprocessorBridge


def test_frustration_loop_triggers_escape():
    circuit = GiantFiberEscapeCircuit()
    bridge = CoprocessorBridge(circuit)

    last_payload = None
    for msg in [
        "Como configuro a rede?",
        "Não entendi bem o primeiro ponto, podes detalhar?",
        "Continua a dar erro.",
        "Não funciona, dá o mesmo erro.",
        "Erro de novo, nada feito???",
    ]:
        last_payload = bridge.process(msg)

    # The 5th turn should have triggered escape mode
    assert last_payload is not None
    assert last_payload.temperature == 0.1
    assert last_payload.num_predict == 80
    assert "CIRCUITO DE FUGA DISPARADO" in last_payload.system_addendum


def test_explicit_negative_feedback():
    circuit = GiantFiberEscapeCircuit()
    bridge = CoprocessorBridge(circuit)

    bridge.process("Tentei A")
    bridge.process("Tentei B")
    pot_before = circuit.membrane_potential
    payload = bridge.process("Nada funciona", explicit_feedback="--")
    # explicit negative feedback should strongly boost
    assert circuit.membrane_potential > pot_before
    # may or may not cross threshold depending on config
    assert circuit.membrane_potential >= 0.0


def test_decay_over_constructive_dialogue():
    circuit = GiantFiberEscapeCircuit(decay_rate=0.5)
    bridge = CoprocessorBridge(circuit)

    bridge.process("Erro aqui")  # raise
    bridge.process("Agora entendi, obrigado pela ajuda detalhada!")  # long calm
    # potential should have decayed significantly
    assert circuit.membrane_potential < circuit.escape_threshold


if __name__ == "__main__":
    pytest.main([__file__, "-v"])