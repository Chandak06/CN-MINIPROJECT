import logging
import time
from typing import Optional

try:
    import ntplib
except ImportError:  # pragma: no cover
    ntplib = None


LOGGER = logging.getLogger(__name__)

NTP_WARNING_INTERVAL_SECONDS = 300
_last_ntp_warning_at = 0.0
_last_ntp_warning_key = ""

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


def fetch_ntp_time(ntp_server: str = "time.google.com", timeout: int = 2) -> Optional[float]:
    global _last_ntp_warning_at
    global _last_ntp_warning_key

    if ntplib is None:
        LOGGER.warning("ntplib is not installed; using system time fallback.")
        return None

    candidates = _candidate_servers(ntp_server)
    if not candidates:
        return None

    client = ntplib.NTPClient()
    errors: list[str] = []
    for server in candidates:
        try:
            response = client.request(server, version=3, timeout=timeout)
            return response.tx_time
        except Exception as exc:
            errors.append(f"{server}: {exc}")

    warning_key = " | ".join(errors)
    now = time.monotonic()
    if warning_key != _last_ntp_warning_key or (now - _last_ntp_warning_at) >= NTP_WARNING_INTERVAL_SECONDS:
        LOGGER.warning("NTP unavailable; using system time. Attempts: %s", warning_key)
        _last_ntp_warning_at = now
        _last_ntp_warning_key = warning_key
    return None


def compute_reference_offset(reference_time: float) -> float:
    return reference_time - time.time()
