"""In-memory HTTP metrics in Prometheus text format."""

from collections import defaultdict
from threading import Lock

_request_counts: dict[tuple[str, str, str], int] = defaultdict(int)
_request_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
_request_duration_count: dict[tuple[str, str], int] = defaultdict(int)
_metrics_lock = Lock()


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def record_http_request(
    method: str,
    path: str,
    status_code: int,
    duration_seconds: float,
) -> None:
    method_label = method.upper()
    path_label = path or "/"
    status_label = str(status_code)

    key_with_status = (method_label, path_label, status_label)
    key_without_status = (method_label, path_label)

    with _metrics_lock:
        _request_counts[key_with_status] += 1
        _request_duration_sum[key_without_status] += max(duration_seconds, 0.0)
        _request_duration_count[key_without_status] += 1


def render_prometheus_metrics() -> str:
    lines: list[str] = [
        "# HELP kra_http_requests_total Total number of HTTP requests",
        "# TYPE kra_http_requests_total counter",
        "# HELP kra_http_request_duration_seconds HTTP request latency in seconds",
        "# TYPE kra_http_request_duration_seconds summary",
    ]

    with _metrics_lock:
        for (method, path, status), count in sorted(_request_counts.items()):
            lines.append(
                "kra_http_requests_total"
                f'{{method="{_escape_label(method)}",path="{_escape_label(path)}",status="{_escape_label(status)}"}} '
                f"{count}"
            )

        for (method, path), total in sorted(_request_duration_sum.items()):
            lines.append(
                "kra_http_request_duration_seconds_sum"
                f'{{method="{_escape_label(method)}",path="{_escape_label(path)}"}} '
                f"{total}"
            )

        for (method, path), count in sorted(_request_duration_count.items()):
            lines.append(
                "kra_http_request_duration_seconds_count"
                f'{{method="{_escape_label(method)}",path="{_escape_label(path)}"}} '
                f"{count}"
            )

    return "\n".join(lines) + "\n"
