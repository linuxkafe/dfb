#!/usr/bin/env python3
"""Interactive CLI for the Giant Fiber coprocessor demo."""

import sys

from src.dfb.coprocessor.bridge import CoprocessorBridge
from src.dfb.coprocessor.giant_fiber import GiantFiberEscapeCircuit


def run_interactive(mock: bool = True) -> None:
    """Run an interactive chat loop using the coprocessor bridge."""
    circuit = GiantFiberEscapeCircuit()
    bridge = CoprocessorBridge(circuit)

    print("FlyBrain coprocessor interactive demo (type 'exit' or 'quit' to leave)")
    print(
        "Telemetry format: "
        "[GF Potential: X.XX | Mode: Normal/ESCAPE FIRED | Temp: X.XX]"
    )
    print("-" * 70)

    while True:
        try:
            user_input = input("User: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break

        # Detect explicit feedback markers
        explicit_feedback = None
        if user_input.endswith(" ++"):
            explicit_feedback = "++"
            user_input = user_input[:-3].strip()
        elif user_input.endswith(" --"):
            explicit_feedback = "--"
            user_input = user_input[:-3].strip()

        payload = bridge.process(user_input, explicit_feedback)
        status = bridge.get_status()

        mode = "ESCAPE FIRED" if status["escape_active"] else "Normal"
        print(
            f"[GF Potential: {status['membrane_potential']:.2f} | "
            f"Mode: {mode} | Temp: {payload.temperature:.2f}]"
        )

        # Mock bot response
        if mock:
            if payload.temperature == 0.1:
                print(
                    "Bot: (escape mode) Direct answer: "
                    "check the service status or restart it."
                )
            else:
                print("Bot: Here is a helpful explanation...")
        else:
            # Placeholder for real Ollama call
            print("Bot: (Ollama call not implemented in demo)")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="FlyBrain coprocessor interactive CLI")
    parser.add_argument(
        "--no-mock", action="store_true", help="Disable mock bot (not implemented)"
    )
    args = parser.parse_args()

    run_interactive(mock=not args.no_mock)
    return 0


if __name__ == "__main__":
    sys.exit(main())
