import threading
import time
from typing import Optional

from ntp_sync import compute_reference_offset, fetch_ntp_time


class MasterClock:
    def __init__(self, ntp_server: str = "pool.ntp.org", sync_interval: int = 30) -> None:
        self.ntp_server = ntp_server
        self.sync_interval = sync_interval
        self._offset = 0.0
        self._last_sync_status = "system-time"
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)

    def now(self) -> float:
        with self._lock:
            offset = self._offset
        return time.time() + offset

    def status(self) -> str:
        with self._lock:
            return self._last_sync_status

    def _sync_loop(self) -> None:
        while not self._stop_event.is_set():
            ntp_time = fetch_ntp_time(self.ntp_server)
            with self._lock:
                if ntp_time is None:
                    self._offset = 0.0
                    self._last_sync_status = "system-time"
                else:
                    self._offset = compute_reference_offset(ntp_time)
                    self._last_sync_status = f"ntp:{self.ntp_server}"
            self._stop_event.wait(self.sync_interval)
