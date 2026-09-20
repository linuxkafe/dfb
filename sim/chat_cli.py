"""Module D — CLI chat loop over the fly-brain + Ollama co-processor.

``python sim/chat_cli.py [--mock] [--base-url URL] [--model NAME]``

Each user turn is fed through the connectome (Modules A+B), converted to
Ollama parameters (Module C), and a telemetry line is printed before the
model's reply:

    [Bússola: 42° | Alerta (Oct): 0.78 | Afinidade: +0.35 | Temp: 0.65]

``++`` / ``--`` reward or punish the mushroom body (DAN plasticity) and do not
reach the model.

The neuronal step is CPU-only, vectorised and non-blocking; the only blocking
call is the Ollama HTTP request itself (bounded by a timeout). ``--mock`` uses a
deterministic local stub instead of the live server.
"""

import argparse
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim.fly_coprocessor import FlyBrain
from sim.neuro_to_ollama import build_request, ollama_params
from sim.semantic_encoder import SemanticEncoder

TELEMETRY = "[Bússola: {compass}° | Alerta (Oct): {oct:.2f} | Afinidade: {aff:+.2f} | Temp: {temp:.2f}]"

BASE_SYSTEM = (
    "És um assistente com um 'cérebro de mosca' (fly-brain). "
    "O teu humor e extensão de resposta seguem o estado neuronal interno."
)


class MockOllama:
    """Deterministic offline stand-in for Ollama."""

    def __init__(self, model: str = "llama3.1:8b"):
        self.model = model
        self.last_payload = None

    def chat(self, payload: dict) -> dict:
        self.last_payload = payload
        params = payload.get("temperature", 0.5)
        if params >= 0.6:
            reply = "Ar fresco! O que mudámos de tema?"
        elif params <= 0.3:
            reply = "Certo. Nota mental."
        else:
            reply = "Recebi. Continuo por aqui."
        return {"message": {"content": reply}}


class OllamaClient:
    """Thin requests-based Ollama ``/api/chat`` client."""

    def __init__(self, base_url: str = "http://steamdeck:11434", model: str = "llama3.1:8b", timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, payload: dict) -> dict:
        payload = {**payload, "keep_alive": "30m"}
        resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fly-brain chatbot CLI")
    parser.add_argument("--mock", action="store_true", help="use a deterministic offline Ollama stub")
    parser.add_argument("--base-url", default="http://steamdeck:11434")
    parser.add_argument("--model", default="llama3.1:8b")
    args = parser.parse_args(argv)

    brain = FlyBrain()
    encoder = SemanticEncoder()
    client: MockOllama | OllamaClient
    if args.mock:
        client = MockOllama(args.model)
    else:
        client = OllamaClient(args.base_url, args.model)
        try:
            client.chat({"model": args.model, "messages": [{"role": "user", "content": "ok"}], "num_predict": 1})
        except requests.RequestException:
            pass

    print("fly-brain co-processor: type a message; ++ / -- to reward/punish; .quit to exit")
    t0 = time.time()
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        t0 += 1.0
        if not raw:
            continue
        if raw == "++":
            state = brain.step(brain.ring.orientation_deg, novelty=0.0, reward=+1.0)
            print("reforço registado (DAN+)")
            continue
        if raw == "--":
            state = brain.step(brain.ring.orientation_deg, novelty=0.0, reward=-1.0)
            print("punição registada (DAN-)")
            continue
        if raw in (".quit", ".exit", "exit", "quit"):
            break

        angle, injection, novelty = encoder(raw, t0)
        state = brain.step(angle, novelty=novelty)
        params = ollama_params(state, BASE_SYSTEM)
        print(TELEMETRY.format(
            compass=int(round(state.orientation_deg)) % 360,
            oct=state.octopamine,
            aff=state.affinity,
            temp=params.temperature,
        ))
        try:
            payload = build_request(raw, state, args.model, BASE_SYSTEM)
            reply = client.chat(payload).get("message", {}).get("content", "")
        except requests.RequestException as exc:
            print(f"(ollama indisponível: {exc})", file=sys.stderr)
            continue
        print(f"  {reply}")

    return 0


if __name__ == "__main__":
    sys.exit(main())