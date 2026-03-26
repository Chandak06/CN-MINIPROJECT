import logging
import socket
import time
import urllib.error
import urllib.request
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Optional

try:
    import ntplib
except ImportError:  # pragma: no cover
    ntplib = None


LOGGER = logging.getLogger(__name__)

NTP_WARNING_INTERVAL_SECONDS = 300
_warning_state = {"at": 0.0, "key": ""}

PRIMARY_NTP_SERVER = "pool.ntp.org"

DEFAULT_NTP_FALLBACKS = (
    PRIMARY_NTP_SERVER,
    "time.google.com",
    "time.cloudflare.com",
    "time.windows.com",
)

DEFAULT_HTTPS_TIME_SOURCES = (
    "https://www.google.com",
    "https://www.cloudflare.com",
    "https://www.microsoft.com",
)


def _candidate_servers(ntp_server: str) -> list[str]:
    raw = (ntp_server or "").strip()
    if not raw or raw.lower() in {"none", "off", "local", "system"}:
        return []

    configured = [part.strip() for part in raw.split(",") if part.strip()]
    candidates: list[str] = []
    seen: set[str] = set()

    def add(server: str) -> None:
        if server and server not in seen:
            candidates.append(server)
            seen.add(server)

    # Always prefer pool.ntp.org first, then any configured extra NTP servers,
    # and only then fall back to the remaining public NTP options.
    add(PRIMARY_NTP_SERVER)
    for server in configured:
        add(server)
    for fallback in DEFAULT_NTP_FALLBACKS:
        add(fallback)
    return candidates


def _should_emit_warning(key: str) -> bool:
    now = time.monotonic()
    last_key = str(_warning_state["key"])
    last_at = float(_warning_state["at"])
    if key != last_key or (now - last_at) >= NTP_WARNING_INTERVAL_SECONDS:
        _warning_state["key"] = key
        _warning_state["at"] = now
        return True
    return False


def _fetch_https_time(timeout: int) -> tuple[Optional[float], str, list[str]]:
    errors: list[str] = []
    for url in DEFAULT_HTTPS_TIME_SOURCES:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=timeout) as response:
                date_header = response.headers.get("Date", "").strip()
                if not date_header:
                    errors.append(f"{url}: missing Date header")
                    continue
                dt = parsedate_to_datetime(date_header)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)  # pragma: no cover
                return dt.timestamp(), url, errors
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors.append(f"{url}: {exc}")
    return None, "", errors


def fetch_reference_time(ntp_server: str = PRIMARY_NTP_SERVER, timeout: int = 2) -> tuple[Optional[float], str]:
    """Return (reference_time, source_label)."""
    candidates = _candidate_servers(ntp_server)
    if not candidates:
        return None, "system-time (manual/system mode)"

    ntp_errors: list[str] = []
    if ntplib is not None:
        client = ntplib.NTPClient()
        ntp_exception = getattr(ntplib, "NTPException", None)
        handled_exceptions: tuple[type[BaseException], ...]
        if isinstance(ntp_exception, type) and issubclass(ntp_exception, BaseException):
            handled_exceptions = (socket.timeout, TimeoutError, OSError, ntp_exception)
        else:
            handled_exceptions = (socket.timeout, TimeoutError, OSError)

        for server in candidates:
            try:
                response = client.request(server, version=3, timeout=timeout)
                return response.tx_time, f"ntp:{server}"
            except handled_exceptions as exc:
                ntp_errors.append(f"{server}: {exc}")
    else:
        ntp_errors.append("ntplib: not installed")

    https_time, https_source, https_errors = _fetch_https_time(timeout=timeout)
    if https_time is not None:
        warning_key = " | ".join(ntp_errors)
        if warning_key and _should_emit_warning(warning_key):
            LOGGER.warning("NTP unavailable; using HTTPS Date fallback. NTP attempts: %s", warning_key)
        return https_time, f"https-date:{https_source}"

    warning_key = " | ".join(ntp_errors + https_errors)
    if _should_emit_warning(warning_key):
        LOGGER.warning("NTP/HTTPS time unavailable; using system time. Attempts: %s", warning_key)
    return None, "system-time (ntp unavailable)"


def fetch_ntp_time(ntp_server: str = PRIMARY_NTP_SERVER, timeout: int = 2) -> Optional[float]:
    reference_time, _ = fetch_reference_time(ntp_server=ntp_server, timeout=timeout)
    return reference_time


def compute_reference_offset(reference_time: float) -> float:
    return reference_time - time.time()
