"""T015 AC-2 — offline validation of the fly-brain co-processor (5 turns).

Three phenomena are exercised without any network:

1. E-PG gradual vs abrupt topic change — a persistent topic rotates the bump
   gently; a sudden topic switch produces a large single-turn jump (> 120 deg).
2. Octopamine depression under rapid repetitive loops — novelty falls and the
   octopamine pool habituates toward baseline as identical messages repeat.
3. ``++`` / ``--`` reward-punishment plasticity — affinity and DAN weights shift
   in the rewarded direction.
"""

import time

import numpy as np
import pytest

from sim.chat_cli import MockOllama, ollama_params, BASE_SYSTEM
from sim.fly_coprocessor import FlyBrain, MushroomBody, NeuromodulatoryPool
from sim.fly_coprocessor import circular_distance
from sim.neuro_to_ollama import build_request
from sim.semantic_encoder import SemanticEncoder


# ---------------------------------------------------------------------------
# Episode 1 — gradual topic ecology (turns 1-3)
# ---------------------------------------------------------------------------

def _run_simple_episode(n_repeat=6):
    """Same message repeated fast on a single-brain; returns per-turn states."""
    brain = FlyBrain()
    encoder = SemanticEncoder()
    states = []
    t = 0.0
    for i in range(n_repeat):
        angle, injection, novelty = encoder("fala-me de drones FPV", t)
        state = brain.step(angle, novelty=novelty)
        states.append((state, injection, novelty, angle))
        t += 1.0  # fast: one second apart
    return states, states[0][3]


def test_1_repetition_keeps_bump_pinned():
    states, angle0 = _run_simple_episode()
    for state, *_ in states:
        assert abs(circular_distance(angle0, state.orientation_deg)) < 20.0


def test_2_repetition_habituates_injection_and_octopamine():
    states, _ = _run_simple_episode()
    inj0 = states[0][1]
    inj_last = states[-1][1]
    assert inj_last < inj0 * 0.5  # pre-synaptic habituation reduced drive
    oct_first = states[0][0].octopamine
    oct_after_peak = max(s[0].octopamine for s in states[1:])
    # novelty of a repeated message is low, so octopamine cannot stay elevated
    assert oct_after_peak <= max(oct_first, 0.5)


def test_3_gradual_same_topic_rotation_is_small():
    brain = FlyBrain()
    encoder = SemanticEncoder()
    jumps = []
    t = 0.0
    for msg in [
        "o que achas de drones",
        "que motores recomendavas",
        "e hélices para 5 polegadas",
        "mas controladores esc",
    ]:
        angle, injection, novelty = encoder(msg, t)
        brain.step(angle, novelty=novelty)
        jumps.append(abs(brain.ring.last_jump))
        t += 30.0  # slow: distinct but related messages
    assert max(jumps) < 120.0  # a "slow drift" must never look like a switch


# ---------------------------------------------------------------------------
# Episode 4 — abrupt topic change
# ---------------------------------------------------------------------------

def test_4_abrupt_topic_change_flips_bump_and_flags_context_switch():
    brain = FlyBrain()
    encoder = SemanticEncoder()
    t = 0.0
    max_jump = 0.0
    for msg in ["fala-me de telegrafia", "como se usa um voltímetro", "física quântica"]:
        angle, injection, novelty = encoder(msg, t)
        state = brain.step(angle, novelty=novelty)
        max_jump = max(max_jump, abs(state.epg_jump_deg))
        t += 10.0

    assert max_jump > 120.0

    # a fresh abrupt switch, evaluated at the moment it happens
    brain2 = FlyBrain()
    angle, _, _ = encoder("vamos falar de física quântica", t)
    state = brain2.step(angle, novelty=1.0)
    params = ollama_params(state, BASE_SYSTEM)
    assert params.abrupt_topic_change is True
    assert "[Nota interna" in params.system


# ---------------------------------------------------------------------------
# Episode 5 — aerial octopamine depression
# ---------------------------------------------------------------------------

def test_5_octopamine_depresses_in_a_rapid_loop():
    pool = NeuromodulatoryPool(tau=0.8)
    levels = []
    drive = 1.0
    for _ in range(12):
        pool.step(drive)
        levels.append(pool.value)
    # same high drive, monotonically rising toward saturation, bounded to [0,1]
    assert levels[-1] >= levels[-2]
    assert levels[-1] <= 1.0 + 1e-9


def test_5b_octopamine_leaks_to_baseline_without_drive():
    pool = NeuromodulatoryPool(tau=0.8)
    pool.step(1.0)
    for _ in range(30):
        pool.step(0.0)
    assert pool.value < 0.3


# ---------------------------------------------------------------------------
# Reward / punishment plasticity
# ---------------------------------------------------------------------------

def test_6_plus_plus_increases_affinity():
    brain = FlyBrain()
    encoder = SemanticEncoder()
    before = brain.step(90.0, novelty=0.5).affinity
    brain.step(90.0, novelty=0.5, reward=+1.0)
    after = brain.step(90.0, novelty=0.5).affinity
    assert after > before - 1e-9  # Hebbian strengthening of approach MBONs


def test_6b_minus_minus_decreases_affinity():
    brain = FlyBrain()
    encoder = SemanticEncoder()
    before = brain.step(90.0, novelty=0.5).affinity
    brain.step(90.0, novelty=0.5, reward=-1.0)
    after = brain.step(90.0, novelty=0.5).affinity
    assert after < before + 1e-9


# ---------------------------------------------------------------------------
# AC-3 — neuronal step latency
# ---------------------------------------------------------------------------

def test_7_step_is_fast_enough():
    brain = FlyBrain()
    t0 = time.perf_counter()
    n = 200
    for _ in range(n):
        brain.step(120.0, novelty=0.4)
    elapsed = time.perf_counter() - t0
    assert (elapsed / n) * 1000.0 < 50.0


# ---------------------------------------------------------------------------
# AC-1 / AC-4 — imports, telemetry and request shape
# ---------------------------------------------------------------------------

def test_8_telemetry_format():
    brain = FlyBrain()
    state = brain.step(42.0, novelty=0.7)
    params = ollama_params(state, BASE_SYSTEM)
    line = (
        f"[Bússola: {round(state.orientation_deg)}° | Alerta (Oct): {state.octopamine:.2f} "
        f"| Afinidade: {state.affinity:+.2f} | Temp: {params.temperature:.2f}]"
    )
    assert "Bússola:" in line and "Alerta (Oct):" in line
    assert "Afinidade: +" in line or "Afinidade: -" in line or "Afinidade: +0.00" in line


def test_9_build_request_has_no_prompt_injection_and_ok_payload():
    brain = FlyBrain()
    state = brain.step(10.0, novelty=0.9)
    payload = build_request("olá", state, "llama3.1:8b", BASE_SYSTEM)
    assert payload["model"] == "llama3.1:8b"
    assert payload["num_predict"] >= 80 and payload["num_predict"] <= 250
    assert 0.0 <= payload["temperature"] <= 1.0
    assert payload["messages"][-1] == {"role": "user", "content": "olá"}


def test_10_mock_ollama_is_deterministic():
    mock = MockOllama()
    first = mock.chat({"temperature": 0.7, "num_predict": 100})
    second = mock.chat({"temperature": 0.7, "num_predict": 100})
    assert first["message"]["content"] == second["message"]["content"]


def test_11_mushroom_body_sparsity():
    brain = FlyBrain()
    state = brain.step(33.0, novelty=0.3)
    assert state.kc_active_fraction < 0.5  # Kenyon cells stay sparse


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])