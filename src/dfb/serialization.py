"""Non-finite float sanitization for the HTTP JSON boundary.

Uvicorn serializes response JSON with ``allow_nan=False``: any ``inf``/``nan``
in a payload raises ``ValueError`` → HTTP 500 (a real production bug — telemetry
timestamps default to 0 before the first message, producing ``float('inf')``
link ages). This module is the single seam that guarantees every JSON response
stays serializable without changing internal semantics: non-finite floats are
replaced by ``null`` at the API boundary.

``SanitizingJSONResponse`` is wired as ``default_response_class`` on the FastAPI
app, so ALL endpoints (plain-dict and ``response_model`` alike, including future
ones) are covered. ``/metrics`` returns Prometheus text via a plain ``Response``
and intentionally bypasses this path.
"""

import json
import math

from starlette.responses import JSONResponse


def json_safe(value):
    """Convert non-JSON-serialisable values (inf/nan) to None."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    return value


class SanitizingJSONResponse(JSONResponse):
    """JSONResponse that flattens non-finite floats to null before encoding.

    Fail-closed: the sanitizer runs first, then ``json.dumps`` with
    ``allow_nan=False`` so any float that slips through still hard-fails
    instead of emitting invalid JSON.
    """

    def render(self, content) -> bytes:
        return json.dumps(
            json_safe(content),
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")
