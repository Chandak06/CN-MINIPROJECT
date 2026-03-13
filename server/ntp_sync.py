import logging
import time
from typing import Optional

try:
    import ntplib
except ImportError:  # pragma: no cover
    ntplib = None


LOGGER = logging.getLogger(__name__)


def fetch_ntp_time(ntp_server: str = "time.google.com", timeout: int = 2) -> Optional[float]:
    if ntplib is None:
        LOGGER.warning("ntplib is not installed; using system time fallback.")
        return None

    client = ntplib.NTPClient()
    try:
        response = client.request(ntp_server, version=3, timeout=timeout)
        return response.tx_time
    except Exception as exc:
        LOGGER.warning("NTP sync failed for %s: %s", ntp_server, exc)
        return None


def compute_reference_offset(reference_time: float) -> float:
    return reference_time - time.time()
