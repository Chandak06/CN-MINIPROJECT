import logging
import socket
import time
from typing import Optional

try:
    import ntplib
except ImportError:  # pragma: no cover
    ntplib = None


LOGGER = logging.getLogger(__name__)

NTP_WARNING_INTERVAL_SECONDS = 300
_warning_state = {"at": 0.0, "key": ""}

DEFAULT_NTP_FALLBACKS = (
    "time.google.com",
    "time.cloudflare.com",
    "time.windows.com",
)


def _candidate_servers(ntp_server: str) -> list[str]:
    raw = (ntp_server or "").strip()
    if not raw or raw.lower() in {"none", "off", "local", "system"}:
        return []

    # Support comma-separated hostnames from CLI/GUI and append known public fallbacks.
    primary = [part.strip() for part in raw.split(",") if part.strip()]
    seen = set(primary)
    for fallback in DEFAULT_NTP_FALLBACKS:
        if fallback not in seen:
            primary.append(fallback)
            seen.add(fallback)
    return primary


def _should_emit_warning(key: str) -> bool:
    now = time.monotonic()
    last_key = str(_warning_state["key"])
    last_at = float(_warning_state["at"])
    if key != last_key or (now - last_at) >= NTP_WARNING_INTERVAL_SECONDS:
        _warning_state["key"] = key
        _warning_state["at"] = now
        return True
    return False


def fetch_ntp_time(ntp_server: str = "time.google.com", timeout: int = 2) -> Optional[float]:
    if ntplib is None:
        warning_key = "ntplib-missing"
        if _should_emit_warning(warning_key):
            LOGGER.warning("ntplib is not installed; using system time fallback.")
        return None

    candidates = _candidate_servers(ntp_server)
    if not candidates:
        return None

    client = ntplib.NTPClient()
    errors: list[str] = []
    ntp_exception = getattr(ntplib, "NTPException", None)
    handled_exceptions: tuple[type[BaseException], ...]
    if isinstance(ntp_exception, type) and issubclass(ntp_exception, BaseException):
        handled_exceptions = (socket.timeout, TimeoutError, OSError, ntp_exception)
    else:
        handled_exceptions = (socket.timeout, TimeoutError, OSError)

    for server in candidates:
        try:
            response = client.request(server, version=3, timeout=timeout)
            return response.tx_time
        except handled_exceptions as exc:
            errors.append(f"{server}: {exc}")

    warning_key = " | ".join(errors)
    if _should_emit_warning(warning_key):
        LOGGER.warning("NTP unavailable; using system time. Attempts: %s", warning_key)
    return None


def compute_reference_offset(reference_time: float) -> float:
    return reference_time - time.time()
