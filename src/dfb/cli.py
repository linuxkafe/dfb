"""CLI for Deck Fly Brain."""
import json
import sys
from dataclasses import is_dataclass, asdict
from typing import Optional, List
import typer
import numpy as np
from rich import print_json

from .client import HttpDeckClient, GrpcDeckClient, create_client_from_env
from .client import (
    HealthResponse, VersionResponse, DecideResponse,
    AdvisoryResponse, SafetyViolationResponse, SafetyStatusResponse,
    TelemetryDecideResponse, TokenResponse, CommandResponse, VerifyResponse,
    MAVLinkTelemetryResponse, TelemetryResponse
)


def _dataclass_encoder(obj):
    """Custom JSON encoder for dataclasses and nested objects."""
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _print_json(data):
    """Print JSON with dataclass support."""
    print_json(data=data, default=_dataclass_encoder)


app = typer.Typer(help="Deck Fly Brain CLI")


def get_client(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
    transport: str = typer.Option("http", "--transport", "-t", help="Transport protocol: http or grpc"),
) -> "HttpDeckClient | GrpcDeckClient":
    host = host or "steamdeck"
    port = port or (8083 if transport == "grpc" else 8082)
    if transport == "grpc":
        return GrpcDeckClient(host=host, port=port)
    return HttpDeckClient(host=host, port=port)


@app.command()
def health(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Check service health."""
    client = get_client(host, port)
    resp = client.health()
    _print_json(resp)


@app.command()
def version(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Get service version."""
    client = get_client(host, port)
    resp = client.version()
    _print_json(resp)


@app.command()
def decide(
    state: str = typer.Argument(..., help="JSON state: {\"position\":[x,y],\"grid\":[[...]],\"exit\":[ex,ey]}"),
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
    transport: str = typer.Option("http", "--transport", "-t", help="Transport protocol: http or grpc"),
):
    """Ask the service for a decision given a maze state (legacy mode, HTTP only)."""
    client = get_client(host, port, transport)
    if not isinstance(client, HttpDeckClient):
        typer.echo("Legacy maze mode only supports HTTP transport", err=True)
        raise typer.Exit(1)
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
    _print_json(resp)


@app.command("decide-telemetry")
def decide_telemetry(
    target_lat: Optional[float] = typer.Option(None, "--lat", help="Target latitude (degrees)"),
    target_lon: Optional[float] = typer.Option(None, "--lon", help="Target longitude (degrees)"),
    target_alt: Optional[float] = typer.Option(None, "--alt", help="Target altitude AGL (meters)"),
    target_speed: Optional[float] = typer.Option(None, "--speed", help="Target ground speed (m/s)"),
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Ask the service for a telemetry-aware advisory decision."""
    client = get_client(host, port)
    resp = client.decide_telemetry(
        target_lat=target_lat,
        target_lon=target_lon,
        target_alt=target_alt,
        target_speed=target_speed,
    )
    _print_json(resp)


@app.command("issue-token")
def issue_token(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Issue a new confirmation token."""
    client = get_client(host, port)
    resp = client.issue_token()
    _print_json(resp)


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
    _print_json(resp)


@app.command("verify-token")
def verify_token(
    token: str = typer.Argument(..., help="Token to verify"),
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Verify a confirmation token without consuming it."""
    client = get_client(host, port)
    resp = client.verify_token(token)
    _print_json(resp)


@app.command("telemetry")
def telemetry(
    host: Optional[str] = typer.Option(None, "--host", "-h", envvar="DFB_HOST"),
    port: Optional[int] = typer.Option(None, "--port", "-p", envvar="DFB_PORT"),
):
    """Get unified telemetry state (MAVLink + CRSF)."""
    client = get_client(host, port)
    resp = client.telemetry()
    _print_json(resp)


if __name__ == "__main__":
    app()