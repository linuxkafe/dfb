# Vision

## Problem

An FPV drone needs a decision-making layer — "Fly Brain" — that reasons about
flight state and makes safe autonomous decisions. This layer currently lives as
firmware on the flight controller (EdgeTX / INAV / ArduPilot), which is
compute-constrained, hard to extend, and impossible to run modern
situational-awareness logic on.

Independent companion computers are expensive and add a second payload.

## Solution

Run the Fly Brain as a **service on Steam Deck** (x86_64 Linux, AMD APU),
accessed remotely via SSH from the development machine.

- **Client (this machine)**: sends requests, provides UI, orchestrates flights.
- **Server (Steam Deck)**: runs the Fly Brain service — telemetry ingestion,
  state estimation, decision engine, MAVLink/CRSF link to the flight controller.

Communication: SSH tunnel / local network. The Steam Deck is the compute node;
the flight controller firmware remains the ultimate safety authority (no FC
firmware changes).

## Value

- One ubiquitous device (Steam Deck) becomes the flight brain host — no custom
  hardware.
- Opens room for higher-level autonomy on commodity hardware.
- Safety preserved: FC firmware untouched, human-in-the-loop for critical
  commands.
- Remote development workflow: code here, compute there.

Success criteria to be defined with the first sprint.