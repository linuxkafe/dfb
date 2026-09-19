#!/usr/bin/env python3
"""Local runner: SSH-deploys monitor to Deck, collects CSV locally."""
import subprocess
import threading
import time
import csv
import sys
from pathlib import Path
from typing import Optional


class DeckMonitor:
    def __init__(self, deck_host: str = "deck@steamdeck", output_dir: str = "aes/verification/T002/raw"):
        self.deck_host = deck_host
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = self.output_dir / "resources.csv"
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        """Deploy monitor script to Deck and start collecting."""
        # Deploy monitor script
        deploy_cmd = [
            "scp", "scripts/monitor_deck.py",
            f"{self.deck_host}:/home/deck/.local/share/dfb/monitor_deck.py"
        ]
        subprocess.run(deploy_cmd, check=True, capture_output=True)

        # Start SSH process that runs monitor and streams stdout
        self._proc = subprocess.Popen(
            ["ssh", self.deck_host, "cd /home/deck/.local/share/dfb && .venv/bin/python monitor_deck.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Start reader thread
        self._thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._thread.start()

        # Wait for first line (header)
        time.sleep(1.5)

    def _read_stdout(self):
        if not self._proc or not self._proc.stdout:
            return

        with open(self.csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            for line in self._proc.stdout:
                if self._stop.is_set():
                    break
                line = line.strip()
                if not line:
                    continue
                if line.startswith("timestamp"):
                    writer.writerow(line.split(","))
                    continue
                try:
                    writer.writerow(line.split(","))
                except Exception:
                    pass
                f.flush()

    def stop(self) -> Path:
        """Stop monitor and return CSV path."""
        self._stop.set()
        if self._proc:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        if self._thread:
            self._thread.join(timeout=2)
        return self.csv_path


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--deck", default="deck@steamdeck")
    parser.add_argument("--output", default="aes/verification/T002/raw")
    parser.add_argument("--duration", type=int, default=60)
    args = parser.parse_args()

    monitor = DeckMonitor(args.deck, args.output)
    monitor.start()
    print(f"Monitor started, collecting for {args.duration}s...", file=sys.stderr)
    time.sleep(args.duration)
    csv_path = monitor.stop()
    print(f"Monitor stopped. Data saved to {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()