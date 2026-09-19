"""CLI for Deck Fly Brain."""
import json
import sys
from typing import Optional, List
import typer
import numpy as np
from rich import print_json

from .client import DeckClient, create_client_from_env


app = typer.Typer(help="Deck Fly Brain CLI")


def get_client(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
) -> "DeckClient":
    from .client import DeckClient
    host = host or "steamdeck"
    port = port or 8082
    return DeckClient(host=host, port=port)


@app.command()
def health(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Check service health."""
    client = get_client(host, port)
    resp = client.health()
    print_json(data=resp.__dict__)


@app.command()
def version(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Get service version."""
    client = get_client(host, port)
    resp = client.version()
    print_json(data=resp.__dict__)


@app.command()
def decide(
    state: str = typer.Argument(..., help="JSON state: {\"position\":[x,y],\"grid\":[[...]],\"exit\":[ex,ey]}"),
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Ask the service for a decision given a maze state."""
    client = get_client(host, port)
    try:
        state_dict = json.loads(state)
    except json.JSONDecodeError as e:
        typer.echo(f"Invalid JSON: {e}", err=True)
        raise typer.Exit(1)
    resp = client.decide(
        position=state_dict["position"],
        grid=state_dict["grid"],
        exit=state_dict["exit"],
    )
    print_json(data=resp.__dict__)


@app.command("issue-token")
def issue_token(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Issue a new confirmation token."""
    client = get_client(host, port)
    resp = client.issue_token()
    print_json(data=resp.__dict__)


@app.command()
def command(
    action: str = typer.Argument(..., help="Action name, e.g. ARM"),
    token: str = typer.Option(..., "--token", "-t", help="Confirmation token from issue-token"),
    params: Optional[str] = typer.Option(None, "--params", help="JSON params dict"),
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Send a safety-critical command requiring a confirmation token."""
    client = get_client(host, port)
    params_dict = json.loads(params) if params else {}
    resp = client.command(action=action, params=params_dict, token=token)
    print_json(data=resp.__dict__)


@app.command("verify-token")
def verify_token(
    token: str = typer.Argument(..., help="Token to verify"),
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Verify a confirmation token without consuming it."""
    client = get_client(host, port)
    resp = client.verify_token(token)
    print_json(data=resp.__dict__)


if __name__ == "__main__":
    app()