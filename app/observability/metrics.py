"""HTTP-level observability.

Tracks request latency and request counts/status codes across all API
endpoints. Exposed at ``GET /metrics`` in Prometheus exposition format,
so it can be scraped alongside the per-agent timings reported by
:mod:`app.observability.tracing`.
"""

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

REQUESTS = Counter("claimflow_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("claimflow_http_request_duration_seconds", "HTTP request latency", ["path"])


def record_request(method: str, path: str, status: int, duration_seconds: float) -> None:
    """Record a single completed HTTP request against the latency/count metrics."""
    LATENCY.labels(path).observe(duration_seconds)
    REQUESTS.labels(method, path, status).inc()


def metrics_response() -> Response:
    """Render current metrics in Prometheus exposition format."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
