"""gRPC server for FlyBrain - runs on port 8083 alongside HTTP/8082."""

import asyncio
import os
import signal
from typing import Optional

import grpc

from src.dfb.grpc import flybrain_pb2_grpc
from src.dfb.grpc_service import FlyBrainServicer


async def create_grpc_server(
    port: int = 8083,
    enable_tls: bool = False,
    cert_file: Optional[str] = None,
    key_file: Optional[str] = None,
) -> grpc.aio.Server:
    """Create and configure gRPC server."""
    server = grpc.aio.server()

    # Add servicer
    servicer = FlyBrainServicer()
    flybrain_pb2_grpc.add_FlyBrainServiceServicer_to_server(servicer, server)

    # Configure port
    if enable_tls and cert_file and key_file:
        with open(cert_file, "rb") as f:
            cert = f.read()
        with open(key_file, "rb") as f:
            key = f.read()
        credentials = grpc.ssl_server_credentials([(key, cert)])
        server.add_secure_port(f"[::]:{port}", credentials)
    else:
        server.add_insecure_port(f"[::]:{port}")

    return server


async def run_grpc_server(
    port: int = 8083,
    enable_tls: bool = False,
    cert_file: Optional[str] = None,
    key_file: Optional[str] = None,
) -> None:
    """Run gRPC server with graceful shutdown handling."""
    server = await create_grpc_server(port, enable_tls, cert_file, key_file)

    # Graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler():
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)

    await server.start()
    print(f"gRPC server started on port {port}")

    try:
        await shutdown_event.wait()
    finally:
        print("Shutting down gRPC server...")
        await server.stop(grace=5)
        await server.wait_for_termination()


if __name__ == "__main__":
    import os
    import signal

    port = int(os.getenv("GRPC_PORT", "8083"))
    enable_tls = os.getenv("GRPC_TLS", "false").lower() == "true"
    cert_file = os.getenv("GRPC_CERT_FILE")
    key_file = os.getenv("GRPC_KEY_FILE")

    asyncio.run(run_grpc_server(port, enable_tls, cert_file, key_file))
