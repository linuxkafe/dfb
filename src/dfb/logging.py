"""Structured JSON logging for Deck Fly Brain."""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Correlation ID context variable
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(cid)


class JSONFormatter(logging.Formatter):
    """JSON log formatter with correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_correlation_id(),
        }

        # Add extra fields
        if hasattr(record, "endpoint"):
            log_obj["endpoint"] = record.endpoint
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "component"):
            log_obj["component"] = record.component
        if hasattr(record, "component_status"):
            log_obj["component_status"] = record.component_status

        # Add exception info
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers = [handler]

    # Reduce noise from dependencies
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("pymavlink").setLevel(logging.WARNING)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests."""

    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
        set_correlation_id(cid)

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = cid
        return response


def log_request(
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: float,
    correlation_id: str = "",
) -> None:
    """Log HTTP request with structured fields."""
    logger = logging.getLogger("dfb.request")
    logger.info(
        f"{method} {endpoint} {status_code}",
        extra={
            "endpoint": endpoint,
            "method": method,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "correlation_id": correlation_id,
        },
    )


def log_component_health(
    component: str, status: str, details: dict, correlation_id: str = ""
) -> None:
    """Log component health change."""
    logger = logging.getLogger("dfb.health")
    logger.info(
        f"Component {component} status: {status}",
        extra={
            "component": component,
            "component_status": status,
            "details": details,
            "correlation_id": correlation_id,
        },
    )


def log_mavlink_event(event: str, details: dict, correlation_id: str = "") -> None:
    """Log MAVLink events (connect, disconnect, reconnect)."""
    logger = logging.getLogger("dfb.mavlink")
    logger.info(
        f"MAVLink {event}",
        extra={
            "event": event,
            "details": details,
            "correlation_id": correlation_id,
        },
    )
