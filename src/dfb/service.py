"""Fly Brain service for Steam Deck — health + version endpoints."""
from fastapi import FastAPI

from src import __version__

app = FastAPI(title="Deck Fly Brain", version=__version__)

@app.get("/health")
async def health():
    return {"status": "ok", "version": __version__}

@app.get("/version")
async def version():
    return {"version": __version__}
