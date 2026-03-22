import argparse
import os
import socket
import ssl
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import messagebox, ttk


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from sync_algorithm import compute_offset_and_delay
from utils.packet_format import build_time_request, decode_packet, encode_packet, validate_reply


DEFAULT_HOST = os.getenv("CLOCKSYNC_SERVER_IP", "127.0.0.1")
DEFAULT_PORT = 6000
DEFAULT_ROUNDS = 10
DEFAULT_DRIFT_SECONDS = 0.5
DEFAULT_INTERVAL_SECONDS = 1.0
BUFFER_SIZE = 2048
SOCKET_TIMEOUT_SECONDS = 5
CERT_FILE = os.path.join(PROJECT_ROOT, "security", "cert.pem")


@dataclass
class SyncRow:
    round_id: int
    server_time: float
    offset: float
    delay: float
    receive_time: float


class ClientSyncGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Secure Client Time Viewer")
        self.geometry("980x650")
        self.minsize(840, 560)

        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.rows: list[SyncRow] = []

        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.hostname_var = tk.StringVar(value="localhost")
        self.rounds_var = tk.StringVar(value=str(DEFAULT_ROUNDS))
        self.drift_var = tk.StringVar(value=str(DEFAULT_DRIFT_SECONDS))
        self.interval_var = tk.StringVar(value=str(DEFAULT_INTERVAL_SECONDS))

        self.status_var = tk.StringVar(value="Idle")
        self.server_time_var = tk.StringVar(value="-")
        self.local_receive_var = tk.StringVar(value="-")

        self._configure_style()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        bg = "#0F172A"
        panel = "#1E293B"
        fg = "#E2E8F0"

        self.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=bg, foreground=fg, font=("Segoe UI Semibold", 16))
        style.configure("PanelLabel.TLabel", background=panel, foreground=fg, font=("Segoe UI", 10))
        style.configure("TButton", padding=6, font=("Segoe UI Semibold", 10))
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=24)
        style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10))

    def _build_ui(self) -> None:
        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Secure Client Time Viewer", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            outer,
            text="Runs TLS sync rounds and shows the exact server time received in each response.",
        ).pack(anchor="w", pady=(2, 10))

        config = ttk.LabelFrame(outer, text="Connection and Sync Settings", padding=12)
        config.pack(fill="x")

        self._entry_row(config, "Server Host", self.host_var, 0)
        self._entry_row(config, "Server Port", self.port_var, 1)
        self._entry_row(config, "TLS Hostname", self.hostname_var, 2)
        self._entry_row(config, "Rounds", self.rounds_var, 3)
        self._entry_row(config, "Simulated Drift (s)", self.drift_var, 4)
        self._entry_row(config, "Interval Between Rounds (s)", self.interval_var, 5)

        actions = ttk.Frame(config)
        actions.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.start_btn = ttk.Button(actions, text="Start Sync", command=self.start_sync)
        self.stop_btn = ttk.Button(actions, text="Stop", command=self.stop_sync, state="disabled")
        self.clear_btn = ttk.Button(actions, text="Clear Table", command=self.clear_table)
        self.start_btn.pack(side="left", padx=(0, 8))
        self.stop_btn.pack(side="left", padx=(0, 8))
        self.clear_btn.pack(side="left")

        status_panel = ttk.Frame(outer, style="Panel.TFrame", padding=10)
        status_panel.pack(fill="x", pady=(12, 10))

        ttk.Label(status_panel, text="Status:", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Label(status_panel, textvariable=self.status_var, style="PanelLabel.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(status_panel, text="Latest Server Time Received:", style="PanelLabel.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0)
        )
        ttk.Label(status_panel, textvariable=self.server_time_var, style="PanelLabel.TLabel").grid(
            row=1, column=1, sticky="w", pady=(4, 0)
        )
        ttk.Label(status_panel, text="Latest Local Receive Time (T4):", style="PanelLabel.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 8), pady=(4, 0)
        )
        ttk.Label(status_panel, textvariable=self.local_receive_var, style="PanelLabel.TLabel").grid(
            row=2, column=1, sticky="w", pady=(4, 0)
        )
        status_panel.columnconfigure(1, weight=1)

        table_frame = ttk.Frame(outer)
        table_frame.pack(fill="both", expand=True)

        columns = ("round", "server_time", "offset", "delay", "receive_time")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "round": "Round",
            "server_time": "Server Time (reference_time)",
            "offset": "Offset (s)",
            "delay": "Delay (s)",
            "receive_time": "Client Receive Time T4",
        }
        widths = {
            "round": 80,
            "server_time": 280,
            "offset": 120,
            "delay": 120,
            "receive_time": 260,
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _entry_row(self, parent: ttk.Widget, label: str, var: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=4)
        ttk.Entry(parent, textvariable=var, width=44).grid(row=row, column=1, sticky="ew", pady=4)
        parent.columnconfigure(1, weight=1)

    def _format_timestamp(self, ts: float) -> str:
        readable = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return f"{readable} ({ts:.6f})"

    def _set_running_ui(self, running: bool) -> None:
        self.start_btn.configure(state="disabled" if running else "normal")
        self.stop_btn.configure(state="normal" if running else "disabled")

    def _friendly_sync_error(self, exc: Exception, host: str, port: int, server_hostname: str) -> str:
        if isinstance(exc, ConnectionRefusedError):
            return (
                f"Connection refused by {host}:{port}.\n\n"
                "Start the TLS server first, for example:\n"
                f"python server/secure_server.py --host 0.0.0.0 --port {port}"
            )

        if isinstance(exc, socket.timeout):
            return (
                f"Connection to {host}:{port} timed out after {SOCKET_TIMEOUT_SECONDS} seconds.\n\n"
                "Check server IP/port and firewall rules on the server machine."
            )

        if isinstance(exc, ssl.SSLCertVerificationError):
            return (
                "TLS certificate verification failed.\n\n"
                f"Current TLS hostname: {server_hostname}\n"
                "Ensure this value matches a SAN entry in security/cert.pem, "
                "then restart the server."
            )

        if isinstance(exc, ssl.SSLError):
            return f"TLS handshake failed: {exc}"

        if isinstance(exc, OSError):
            return f"Network error while connecting to {host}:{port}: {exc}"

        return str(exc)

    def start_sync(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        try:
            host = self.host_var.get().strip() or DEFAULT_HOST
            port = int(self.port_var.get().strip())
            if port < 1 or port > 65535:
                raise ValueError
            rounds = max(1, int(self.rounds_var.get().strip()))
            drift = float(self.drift_var.get().strip())
            interval_seconds = max(0.0, float(self.interval_var.get().strip()))
            server_hostname = self.hostname_var.get().strip() or host
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid host/port/rounds/drift/interval values.")
            return

        if not os.path.exists(CERT_FILE):
            messagebox.showerror("Missing certificate", "security/cert.pem not found. Run generate_cert.py first.")
            return

        self.stop_event.clear()
        self.status_var.set("Running...")
        self._set_running_ui(True)

        self.worker = threading.Thread(
            target=self._run_sync_session,
            args=(host, port, server_hostname, rounds, drift, interval_seconds),
            daemon=True,
        )
        self.worker.start()

    def stop_sync(self) -> None:
        self.stop_event.set()
        self.status_var.set("Stopping...")

    def clear_table(self) -> None:
        self.rows.clear()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.server_time_var.set("-")
        self.local_receive_var.set("-")
        if not (self.worker and self.worker.is_alive()):
            self.status_var.set("Idle")

    def _run_sync_session(
        self,
        host: str,
        port: int,
        server_hostname: str,
        rounds: int,
        local_drift: float,
        interval_seconds: float,
    ) -> None:
        context = ssl.create_default_context()
        context.load_verify_locations(CERT_FILE)

        completed = 0
        for request_id in range(1, rounds + 1):
            if self.stop_event.is_set():
                break

            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_socket:
                    raw_socket.settimeout(SOCKET_TIMEOUT_SECONDS)
                    with context.wrap_socket(raw_socket, server_hostname=server_hostname) as secure_socket:
                        secure_socket.connect((host, port))

                        t1 = time.time() + local_drift
                        request = build_time_request(request_id=request_id, t1=t1)
                        secure_socket.sendall(encode_packet(request))

                        response_data = secure_socket.recv(BUFFER_SIZE)
                        t4 = time.time() + local_drift

                packet = decode_packet(response_data)
                validate_reply(packet)

                if int(packet.get("id", -1)) != request_id:
                    raise ValueError("Response ID does not match request ID")

                sync_values = compute_offset_and_delay(t1=t1, t2=packet["T2"], t3=packet["T3"], t4=t4)
                row = SyncRow(
                    round_id=request_id,
                    server_time=float(packet["reference_time"]),
                    offset=float(sync_values["offset"]),
                    delay=float(sync_values["delay"]),
                    receive_time=t4,
                )
                completed += 1

                self.after(0, self._append_row, row)
                self.after(0, self.status_var.set, f"Running... ({completed}/{rounds})")
            except (
                ConnectionRefusedError,
                socket.timeout,
                ssl.SSLError,
                OSError,
                ValueError,
                KeyError,
                TypeError,
            ) as exc:
                message = self._friendly_sync_error(exc, host=host, port=port, server_hostname=server_hostname)
                self.after(0, self._handle_error, message)
                return

            slept = 0.0
            while slept < interval_seconds and not self.stop_event.is_set():
                chunk = min(0.1, interval_seconds - slept)
                time.sleep(chunk)
                slept += chunk

        if self.stop_event.is_set():
            self.after(0, self._finish_status, "Stopped")
        else:
            self.after(0, self._finish_status, f"Completed ({completed}/{rounds})")

    def _append_row(self, row: SyncRow) -> None:
        self.rows.append(row)
        self.server_time_var.set(self._format_timestamp(row.server_time))
        self.local_receive_var.set(self._format_timestamp(row.receive_time))
        self.tree.insert(
            "",
            "end",
            values=(
                row.round_id,
                self._format_timestamp(row.server_time),
                f"{row.offset:.6f}",
                f"{row.delay:.6f}",
                self._format_timestamp(row.receive_time),
            ),
        )

    def _handle_error(self, message: str) -> None:
        self._set_running_ui(False)
        self.status_var.set("Error")
        messagebox.showerror("Sync failed", message)

    def _finish_status(self, message: str) -> None:
        self._set_running_ui(False)
        self.status_var.set(message)

    def _on_close(self) -> None:
        self.stop_event.set()
        self.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Client-side GUI for secure clock sync")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--server-hostname", default="localhost")
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--drift", type=float, default=DEFAULT_DRIFT_SECONDS)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = ClientSyncGUI()
    app.host_var.set(args.host)
    app.port_var.set(str(args.port))
    app.hostname_var.set(args.server_hostname)
    app.rounds_var.set(str(args.rounds))
    app.drift_var.set(str(args.drift))
    app.interval_var.set(str(args.interval))
    app.mainloop()


if __name__ == "__main__":
    main()