"""Fly Brain service for Steam Deck — health + version + decide endpoints."""
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

from src import __version__

app = FastAPI(title="Deck Fly Brain", version=__version__)


class DecideRequest(BaseModel):
    position: List[int]
    grid: List[List[int]]
    exit: List[int]


class DecideResponse(BaseModel):
    action: str
    confidence: float


@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}


@app.get("/version")
async def version():
    return {"version": __version__}


@app.post("/decide", response_model=DecideResponse)
async def decide(payload: DecideRequest):
    """
    Stub decision endpoint for maze fly.
    Input: {"position": [x,y], "grid": [[0,1,...]], "exit": [ex,ey]}
    Output: {"action": "UP|DOWN|LEFT|RIGHT", "confidence": 0.5}
    Greedy: move toward exit preferring larger delta axis.
    """
    pos = payload.position
    exit_pos = payload.exit
    dx = exit_pos[0] - pos[0]
    dy = exit_pos[1] - pos[1]

    if abs(dx) >= abs(dy):
        action = "RIGHT" if dx > 0 else "LEFT"
    else:
        action = "DOWN" if dy > 0 else "UP"

    return DecideResponse(action=action, confidence=0.5)

