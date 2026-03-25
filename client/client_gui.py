import csv
import argparse
import json
import os
import socket
import ssl
import statistics
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


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
DEFAULT_INTERVAL_SECONDS = 1.0
BUFFER_SIZE = 2048
SOCKET_TIMEOUT_SECONDS = 5
CERT_FILE = os.path.join(PROJECT_ROOT, "security", "cert.pem")
DEFAULT_OUTPUT_CSV = os.path.join(PROJECT_ROOT, "results", "client_sync_data.csv")
DEFAULT_ANALYSIS_PLOT = os.path.join(PROJECT_ROOT, "results", "client_sync_plot.png")


@dataclass
class SyncRow:
    round_id: int
    server_time: float
    offset: float
    delay: float
    receive_time: float
    elapsed: float
    time_source: str


class ClientSyncGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Secure Client Time Sync")
        self.geometry("1200x750")
        self.minsize(1000, 650)

        self.worker: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.rows: list[SyncRow] = []

        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.protocol_var = tk.StringVar(value="TLS/TCP")
        self.hostname_var = tk.StringVar(value=DEFAULT_HOST)
        self.rounds_var = tk.StringVar(value=str(DEFAULT_ROUNDS))
        self.interval_var = tk.StringVar(value=str(DEFAULT_INTERVAL_SECONDS))
        self.output_var = tk.StringVar(value=DEFAULT_OUTPUT_CSV)
        self.analysis_input_var = tk.StringVar(value=DEFAULT_OUTPUT_CSV)
        self.analysis_output_var = tk.StringVar(value=DEFAULT_ANALYSIS_PLOT)

        self.status_var = tk.StringVar(value="Idle")
        self.server_time_var = tk.StringVar(value="-")
        self.local_receive_var = tk.StringVar(value="-")
        self.server_source_var = tk.StringVar(value="-")
        self.live_local_time_var = tk.StringVar(value="-")
        self.live_offset_display_var = tk.StringVar(value="-")
        self.live_time_var = tk.StringVar(value="-")
        self.live_time_status_var = tk.StringVar(value="Using local clock")
        self.live_offset_seconds = 0.0
        self.live_synced = False

        self._configure_style()
        self._build_ui()
        self.protocol_var.trace_add("write", self._on_protocol_changed)
        self.after(120, self._tick_live_time)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_protocol_changed(self, *_args: object) -> None:
        protocol = self.protocol_var.get()
        if protocol == "UDP" and self.port_var.get().strip() == "6000":
            self.port_var.set("5005")
        elif protocol == "TLS/TCP" and self.port_var.get().strip() == "5005":
            self.port_var.set("6000")

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        bg = "#081423"
        panel = "#10243A"
        panel_alt = "#16314E"
        card = "#1A3A5C"
        fg = "#E6F0FA"
        muted = "#9CB2C9"
        accent = "#46D28B"

        self.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("AltPanel.TFrame", background=panel_alt)
        style.configure("Card.TFrame", background=card)
        style.configure("Header.TLabel", background=bg, foreground=fg, font=("Segoe UI Semibold", 19))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
        style.configure("PanelLabel.TLabel", background=panel, foreground=fg, font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background=card, foreground=muted, font=("Segoe UI Semibold", 10))
        style.configure("CardValue.TLabel", background=card, foreground=fg, font=("Segoe UI Semibold", 20))
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=6)
        style.configure("Primary.TButton", foreground="#062213")
        style.map("Primary.TButton", background=[("!disabled", accent)], foreground=[("!disabled", "#062213")])
        style.configure("StatusGreen.TLabel", background=panel, foreground="#4ADE80", font=("Segoe UI Semibold", 10))
        style.configure("StatusRed.TLabel", background=panel, foreground="#F97373", font=("Segoe UI Semibold", 10))
        style.configure("TLabelframe", background=panel, foreground=fg)
        style.configure("TLabelframe.Label", background=panel, foreground=fg, font=("Segoe UI Semibold", 10))
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI Semibold", 10), padding=(14, 8))
        style.configure("Treeview", rowheight=24, fieldbackground="#0B1D30", background="#0B1D30", foreground=fg)
        style.configure("Treeview.Heading", background="#12304D", foreground=fg, font=("Segoe UI Semibold", 10))

    def _build_ui(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=14, pady=12)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="Secure Client Time Sync", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Connect to TLS server, perform time synchronization, and analyze clock offset and delay patterns.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=(8, 12))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        self.sync_tab = ttk.Frame(notebook)
        self.live_time_tab = ttk.Frame(notebook)
        self.analysis_tab = ttk.Frame(notebook)
        notebook.add(self.sync_tab, text="Client Sync")
        notebook.add(self.live_time_tab, text="Live Time")
        notebook.add(self.analysis_tab, text="Analysis")

        self._build_sync_tab()
        self._build_live_time_tab()
        self._build_analysis_tab()

    def _build_sync_tab(self) -> None:
        outer = ttk.Frame(self.sync_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        cfg = ttk.LabelFrame(outer, text="Connection and Sync Settings", padding=12)
        cfg.pack(fill="x")

        self._build_labeled_entry(cfg, "Protocol", self.protocol_var, 0, options=["TLS/TCP", "UDP"])
        self._build_labeled_entry(cfg, "Server Host", self.host_var, 1)
        self._build_labeled_entry(cfg, "Server Port", self.port_var, 2)
        self._build_labeled_entry(cfg, "TLS Hostname", self.hostname_var, 3)
        self._build_labeled_entry(cfg, "Rounds", self.rounds_var, 4)
        self._build_labeled_entry(cfg, "Interval Between Rounds (s)", self.interval_var, 5)
        self._build_labeled_entry(cfg, "Output CSV", self.output_var, 6)

        actions = ttk.Frame(cfg)
        actions.grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Choose Output", command=self._choose_output_path).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Start Sync", style="Primary.TButton", command=self.start_sync).pack(side="left", padx=(0, 8))
        self.stop_btn = ttk.Button(actions, text="Stop", command=self.stop_sync, state="disabled")
        self.stop_btn.pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Clear Table", command=self.clear_table).pack(side="left")

        status_frame = ttk.Frame(outer)
        status_frame.pack(fill="x", pady=(12, 10))
        status_frame.columnconfigure((0, 1, 2, 3), weight=1)
        self._build_kpi_card(status_frame, "Status", self.status_var, 0)
        self._build_kpi_card(status_frame, "Latest Source", self.server_source_var, 1)

        ttk.Label(outer, text="Sync Samples", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 4))
        table_frame = ttk.Frame(outer)
        table_frame.pack(fill="both", expand=True)

        columns = ("round", "server_time", "offset", "delay", "receive_time")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        headings = {
            "round": "Round",
            "server_time": "Server Time",
            "offset": "Offset (s)",
            "delay": "Delay (s)",
            "receive_time": "Client T4 (local)",
        }
        widths = {
            "round": 70,
            "server_time": 220,
            "offset": 120,
            "delay": 120,
            "receive_time": 240,
        }
        for key in columns:
            self.tree.heading(key, text=headings[key])
            self.tree.column(key, width=widths[key], anchor="center")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def _build_kpi_card(self, parent: ttk.Widget, label: str, value_var: tk.StringVar, column: int) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.grid(row=0, column=column, sticky="nsew", padx=6)
        ttk.Label(card, text=label, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=value_var, style="CardValue.TLabel").pack(anchor="w", pady=(4, 0))

    def _build_live_time_tab(self) -> None:
        outer = ttk.Frame(self.live_time_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        cfg = ttk.LabelFrame(outer, text="Server Time Source", padding=12)
        cfg.pack(fill="x")

        self._build_labeled_entry(cfg, "Protocol", self.protocol_var, 0, options=["TLS/TCP", "UDP"])
        self._build_labeled_entry(cfg, "Server Host", self.host_var, 1)
        self._build_labeled_entry(cfg, "Server Port", self.port_var, 2)
        self._build_labeled_entry(cfg, "TLS Hostname", self.hostname_var, 3)

        actions = ttk.Frame(cfg)
        actions.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Sync From Server", style="Primary.TButton", command=self.sync_live_time).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Use Local Clock", command=self.reset_live_time_to_local).pack(side="left")

        local_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        local_panel.pack(fill="x", pady=(12, 6))
        ttk.Label(local_panel, text="Local Clock", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(local_panel, textvariable=self.live_local_time_var, style="PanelLabel.TLabel", font=("Consolas", 18, "bold")).grid(row=0, column=1, sticky="w")

        offset_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        offset_panel.pack(fill="x", pady=6)
        ttk.Label(offset_panel, text="Offset Applied", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(offset_panel, textvariable=self.live_offset_display_var, style="PanelLabel.TLabel", font=("Consolas", 14)).grid(row=0, column=1, sticky="w")

        synced_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        synced_panel.pack(fill="x", pady=6)
        ttk.Label(synced_panel, text="Synced Server Time", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(synced_panel, textvariable=self.live_time_var, style="PanelLabel.TLabel", font=("Consolas", 18, "bold")).grid(row=0, column=1, sticky="w")

        status_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        status_panel.pack(fill="x")
        ttk.Label(status_panel, text="Status", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(status_panel, textvariable=self.live_time_status_var, style="PanelLabel.TLabel").grid(row=0, column=1, sticky="w")

    def _build_labeled_entry(
        self,
        parent: ttk.Widget,
        label: str,
        var: tk.StringVar,
        row: int,
        options: list[str] | None = None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
        if options:
            ttk.Combobox(parent, textvariable=var, values=options, state="readonly", width=45).grid(
                row=row, column=1, sticky="ew", pady=6
            )
        else:
            ttk.Entry(parent, textvariable=var, width=48).grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

    def _build_analysis_tab(self) -> None:
        outer = ttk.Frame(self.analysis_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        top = ttk.LabelFrame(outer, text="Analysis Configuration", padding=12)
        top.pack(fill="x")

        self._build_labeled_entry(top, "Input CSV", self.analysis_input_var, 0)
        self._build_labeled_entry(top, "Output Plot (optional)", self.analysis_output_var, 1)

        actions = ttk.Frame(top)
        actions.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Choose CSV", command=self._choose_input_csv).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Load CSV", command=self.load_csv_table_and_plot).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Drift Estimator", style="Primary.TButton", command=self.run_drift_analysis).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Accuracy Eval", command=self.run_accuracy_analysis).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Generate Plot", command=self.run_plot_script).pack(side="left")

        middle = ttk.Frame(outer)
        middle.pack(fill="both", expand=True, pady=(12, 0))
        middle.columnconfigure(0, weight=1)
        middle.columnconfigure(1, weight=1)
        middle.rowconfigure(0, weight=1)

        table_panel = ttk.Frame(middle, style="AltPanel.TFrame", padding=12)
        plot_panel = ttk.Frame(middle, style="AltPanel.TFrame", padding=12)
        table_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        plot_panel.grid(row=0, column=1, sticky="nsew")

        ttk.Label(table_panel, text="Latest Samples", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 6))
        self.analysis_tree = ttk.Treeview(
            table_panel,
            columns=("round", "offset", "delay", "elapsed"),
            show="headings",
            height=15,
        )
        for col, width in (("round", 80), ("offset", 130), ("delay", 130), ("elapsed", 130)):
            self.analysis_tree.heading(col, text=col.capitalize())
            self.analysis_tree.column(col, width=width, anchor="center")

        table_scroll = ttk.Scrollbar(table_panel, orient="vertical", command=self.analysis_tree.yview)
        self.analysis_tree.configure(yscrollcommand=table_scroll.set)
        self.analysis_tree.pack(side="left", fill="both", expand=True)
        table_scroll.pack(side="right", fill="y")

        ttk.Label(plot_panel, text="Offset and Delay Trend", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 6))
        self.figure = Figure(figsize=(5.6, 4.0), dpi=100)
        self.ax_offset = self.figure.add_subplot(211)
        self.ax_delay = self.figure.add_subplot(212)
        self._style_analysis_plot()
        self.figure.tight_layout(pad=1.8)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _style_analysis_plot(self) -> None:
        """Apply dark theme styling to analysis plots."""
        for ax in [self.ax_offset, self.ax_delay]:
            ax.set_facecolor("#0B1D30")
            ax.tick_params(colors="#DDE9F7")
            ax.grid(alpha=0.25, color="#4A6D90")
            for spine in ax.spines.values():
                spine.set_color("#55799D")
        self.ax_offset.set_title("Offset Trend", color="#E6F0FA")
        self.ax_offset.set_ylabel("Offset (s)", color="#E6F0FA")
        self.ax_delay.set_title("Delay Trend", color="#E6F0FA")
        self.ax_delay.set_ylabel("Delay (s)", color="#E6F0FA")
        self.ax_delay.set_xlabel("Round", color="#E6F0FA")

    def _tick_live_time(self) -> None:
        now = time.time()
        local_display = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.live_local_time_var.set(local_display)

        if self.live_synced and self.live_offset_seconds != 0.0:
            sign = "+" if self.live_offset_seconds > 0 else "-"
            self.live_offset_display_var.set(f"{sign} {abs(self.live_offset_seconds):.6f} seconds")
        else:
            self.live_offset_display_var.set("No sync applied (0.000000 seconds)")

        synced_now = now + (self.live_offset_seconds if self.live_synced else 0.0)
        synced_display = datetime.fromtimestamp(synced_now).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        self.live_time_var.set(synced_display)

        self.after(120, self._tick_live_time)

    def sync_live_time(self) -> None:
        try:
            host = self.host_var.get().strip() or DEFAULT_HOST
            port = int(self.port_var.get().strip())
            if port < 1 or port > 65535:
                raise ValueError
            server_hostname = self.hostname_var.get().strip() or host
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid host/port values.")
            return

        protocol = self.protocol_var.get()
        if protocol == "TLS/TCP" and not os.path.exists(CERT_FILE):
            messagebox.showerror("Missing certificate", "security/cert.pem not found. Run generate_cert.py first.")
            return

        self.live_time_status_var.set("Syncing from server...")
        worker = threading.Thread(
            target=self._sync_live_time_worker,
            args=(host, port, server_hostname, protocol),
            daemon=True,
        )
        worker.start()

    def _sync_live_time_worker(self, host: str, port: int, server_hostname: str, protocol: str) -> None:
        try:
            request_id = int(time.time() * 1000) % 1_000_000
            packet, t1, t4 = self._request_time_sample(
                host=host,
                port=port,
                server_hostname=server_hostname,
                protocol=protocol,
                request_id=request_id,
            )

            if int(packet.get("id", -1)) != request_id:
                raise ValueError("Response ID does not match request ID")

            sync_values = compute_offset_and_delay(t1=t1, t2=packet["T2"], t3=packet["T3"], t4=t4)
            source = str(packet.get("time_source", "unknown"))
            self.after(0, self._on_live_time_synced, float(sync_values["offset"]), float(sync_values["delay"]), source)
        except Exception as exc:
            self.after(0, self._on_live_time_sync_failed, str(exc))

    def _on_live_time_synced(self, offset: float, delay: float, source: str) -> None:
        self.live_offset_seconds = offset
        self.live_synced = True
        self.server_source_var.set(source)
        self.live_time_status_var.set(f"Synced (delay {delay:.4f}s, offset {offset:.4f}s, source {source})")

    def _on_live_time_sync_failed(self, message: str) -> None:
        self.live_time_status_var.set("Sync failed; using local clock")
        messagebox.showerror("Live Time Sync Failed", message)

    def reset_live_time_to_local(self) -> None:
        self.live_synced = False
        self.live_offset_seconds = 0.0
        self.live_time_status_var.set("Using local clock")

    def _is_server_reachable(self, host: str, port: int, protocol: str, timeout_seconds: float = 2.0) -> bool:
        if protocol == "UDP":
            return True
        try:
            with socket.create_connection((host, port), timeout=timeout_seconds):
                return True
        except OSError:
            return False

    def _request_time_sample(
        self,
        host: str,
        port: int,
        server_hostname: str,
        protocol: str,
        request_id: int,
    ) -> tuple[dict[str, float], float, float]:
        request = build_time_request(request_id=request_id, t1=time.time())
        t1 = float(request["T1"])

        if protocol == "UDP":
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp_socket:
                udp_socket.settimeout(SOCKET_TIMEOUT_SECONDS)
                udp_socket.sendto(encode_packet(request), (host, port))
                response_data, _ = udp_socket.recvfrom(BUFFER_SIZE)
                t4 = time.time()
        else:
            context = ssl.create_default_context()
            context.load_verify_locations(CERT_FILE)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_socket:
                raw_socket.settimeout(SOCKET_TIMEOUT_SECONDS)
                with context.wrap_socket(raw_socket, server_hostname=server_hostname) as secure_socket:
                    secure_socket.connect((host, port))
                    secure_socket.sendall(encode_packet(request))
                    response_data = secure_socket.recv(BUFFER_SIZE)
                    t4 = time.time()

        packet = decode_packet(response_data)
        validate_reply(packet)
        return packet, t1, t4

    def _choose_input_csv(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select sync_data.csv",
            initialdir=os.path.join(PROJECT_ROOT, "results"),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.analysis_input_var.set(selected)

    def _choose_output_path(self) -> None:
        selected = filedialog.asksaveasfilename(
            title="Select output CSV",
            defaultextension=".csv",
            initialdir=os.path.join(PROJECT_ROOT, "results"),
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if selected:
            self.output_var.set(selected)

    def _friendly_sync_error(self, exc: Exception, host: str, port: int, server_hostname: str) -> str:
        if isinstance(exc, ConnectionRefusedError):
            protocol = self.protocol_var.get()
            if protocol == "UDP":
                return (
                    f"Connection failed for UDP target {host}:{port}.\n\n"
                    "Start the UDP server first, for example:\n"
                    f"python server/server.py --host 0.0.0.0 --port {port}"
                )
            return f"Connection refused by {host}:{port}.\n\nStart the TLS server first, for example:\npython server/secure_server.py --host 0.0.0.0 --port {port}"
        if isinstance(exc, socket.timeout):
            return f"Connection to {host}:{port} timed out after {SOCKET_TIMEOUT_SECONDS} seconds.\n\nCheck server IP/port and firewall rules."
        if isinstance(exc, ssl.SSLCertVerificationError):
            return f"TLS certificate verification failed.\n\nReason: {exc}\nCurrent TLS hostname: {server_hostname}\nEnsure the client trusts security/cert.pem."
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
            interval_seconds = max(0.0, float(self.interval_var.get().strip()))
            server_hostname = self.hostname_var.get().strip() or host
        except ValueError:
            messagebox.showerror("Invalid input", "Please enter valid host/port/rounds/interval values.")
            return

        protocol = self.protocol_var.get()
        if protocol == "TLS/TCP" and not os.path.exists(CERT_FILE):
            messagebox.showerror("Missing certificate", "security/cert.pem not found. Run generate_cert.py first.")
            return

        if not self._is_server_reachable(host, port, protocol=protocol):
            server_hint = "secure_server.py" if protocol == "TLS/TCP" else "server.py"
            messagebox.showerror("Server unavailable", f"No server is reachable at {host}:{port}. Start {server_hint} first.")
            self.status_var.set("Server unavailable")
            return

        output_path = self._resolve_project_path(self.output_var.get().strip(), DEFAULT_OUTPUT_CSV)
        if not output_path.lower().endswith(".csv"):
            messagebox.showerror("Invalid output path", "Output path must end with .csv")
            return
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w", newline="", encoding="utf-8") as csv_file:
                csv_file.write("round,offset,delay,elapsed,reference_time,time_source\n")
        except OSError as exc:
            messagebox.showerror("Output error", f"Unable to prepare output CSV: {exc}")
            return

        self.output_var.set(output_path)
        self.analysis_input_var.set(output_path)

        self.stop_event.clear()
        self.status_var.set("Running...")
        self.stop_btn.configure(state="normal")
        self.worker = threading.Thread(
            target=self._run_sync_session,
            args=(host, port, server_hostname, protocol, rounds, interval_seconds),
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
        self.server_source_var.set("-")
        if not (self.worker and self.worker.is_alive()):
            self.status_var.set("Idle")

    def _run_sync_session(
        self,
        host: str,
        port: int,
        server_hostname: str,
        protocol: str,
        rounds: int,
        interval_seconds: float,
    ) -> None:
        output_path = self._resolve_project_path(self.output_var.get().strip(), DEFAULT_OUTPUT_CSV)
        start_perf = time.perf_counter()

        completed = 0
        for request_id in range(1, rounds + 1):
            if self.stop_event.is_set():
                break

            try:
                packet, t1, t4 = self._request_time_sample(
                    host=host,
                    port=port,
                    server_hostname=server_hostname,
                    protocol=protocol,
                    request_id=request_id,
                )

                if int(packet.get("id", -1)) != request_id:
                    raise ValueError("Response ID does not match request ID")

                sync_values = compute_offset_and_delay(t1=t1, t2=packet["T2"], t3=packet["T3"], t4=t4)
                row = SyncRow(
                    round_id=request_id,
                    server_time=float(packet["reference_time"]),
                    offset=float(sync_values["offset"]),
                    delay=float(sync_values["delay"]),
                    receive_time=t4,
                    elapsed=time.perf_counter() - start_perf,
                    time_source=str(packet.get("time_source", "unknown")),
                )
                completed += 1

                self._append_csv_row(output_path, row)

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
            self.after(0, self._apply_post_sync_correction)
            self.after(0, self.load_csv_table_and_plot)

    def _append_row(self, row: SyncRow) -> None:
        self.rows.append(row)
        self.server_source_var.set(row.time_source)
        self.tree.insert(
            "",
            "end",
            values=(
                row.round_id,
                datetime.fromtimestamp(row.server_time).strftime("%Y-%m-%d %H:%M:%S"),
                f"{row.offset:.6f}",
                f"{row.delay:.6f}",
                datetime.fromtimestamp(row.receive_time).strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )

    def _append_csv_row(self, csv_path: str, row: SyncRow) -> None:
        try:
            with open(csv_path, "a", newline="", encoding="utf-8") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [
                        row.round_id,
                        f"{row.offset:.6f}",
                        f"{row.delay:.6f}",
                        f"{row.elapsed:.3f}",
                        f"{row.server_time:.6f}",
                        row.time_source,
                    ]
                )
        except OSError as exc:
            self.after(0, self._handle_error, f"Failed to write output CSV: {exc}")

    def _resolve_project_path(self, path_value: str, default: str) -> str:
        raw = path_value.strip() or default
        if os.path.isabs(raw):
            return raw
        return os.path.join(PROJECT_ROOT, raw)

    def _run_analysis_script(self, label: str, args: list[str]) -> None:
        command = [sys.executable, "-u"] + args
        try:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as exc:
            messagebox.showerror(label, f"Failed to start analysis script: {exc}")
            return

        if completed.returncode != 0:
            details = (completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")
            messagebox.showerror(label, f"{label} failed.\n\n{details.strip() or "No output received."}")
            return

        output = ((completed.stdout or "") + ("\n" + completed.stderr if completed.stderr else "")).strip()
        if output:
            messagebox.showinfo(label, output)
        else:
            messagebox.showinfo(label, f"{label} completed successfully.")

    def run_drift_analysis(self) -> None:
        input_path = self._resolve_project_path(self.analysis_input_var.get().strip(), DEFAULT_OUTPUT_CSV)
        self.analysis_input_var.set(input_path)
        if not os.path.exists(input_path):
            messagebox.showerror("Missing file", "Input CSV file was not found.")
            return
        self._run_analysis_script("Drift Estimator", [os.path.join("analysis", "drift_estimator.py"), "--input", input_path])

    def run_accuracy_analysis(self) -> None:
        input_path = self._resolve_project_path(self.analysis_input_var.get().strip(), DEFAULT_OUTPUT_CSV)
        self.analysis_input_var.set(input_path)
        if not os.path.exists(input_path):
            messagebox.showerror("Missing file", "Input CSV file was not found.")
            return
        self._run_analysis_script(
            "Accuracy Evaluator", [os.path.join("analysis", "accuracy_evaluator.py"), "--input", input_path]
        )

    def run_plot_script(self) -> None:
        input_path = self._resolve_project_path(self.analysis_input_var.get().strip(), DEFAULT_OUTPUT_CSV)
        self.analysis_input_var.set(input_path)
        if not os.path.exists(input_path):
            messagebox.showerror("Missing file", "Input CSV file was not found.")
            return

        args = [os.path.join("analysis", "plot_results.py"), "--input", input_path]
        output_path = self.analysis_output_var.get().strip()
        if output_path:
            output_abs = self._resolve_project_path(output_path, DEFAULT_ANALYSIS_PLOT)
            self.analysis_output_var.set(output_abs)
            args += ["--output", output_abs]
        self._run_analysis_script("Plot Generator", args)

    def load_csv_table_and_plot(self) -> None:
        csv_path = self._resolve_project_path(self.analysis_input_var.get().strip(), DEFAULT_OUTPUT_CSV)
        self.analysis_input_var.set(csv_path)
        if not os.path.exists(csv_path):
            messagebox.showerror("Missing file", "Input CSV file was not found.")
            return

        rounds: list[float] = []
        offsets: list[float] = []
        delays: list[float] = []

        for item in self.analysis_tree.get_children():
            self.analysis_tree.delete(item)

        with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                try:
                    round_val = float(row.get("round", 0))
                    offset_val = float(row.get("offset", 0))
                    delay_val = float(row.get("delay", 0))
                    elapsed_val = float(row.get("elapsed", 0))
                except (TypeError, ValueError):
                    continue

                rounds.append(round_val)
                offsets.append(offset_val)
                delays.append(delay_val)
                self.analysis_tree.insert(
                    "",
                    "end",
                    values=(f"{round_val:.0f}", f"{offset_val:.6f}", f"{delay_val:.6f}", f"{elapsed_val:.3f}"),
                )

        self.ax_offset.clear()
        self.ax_delay.clear()

        if rounds:
            self.ax_offset.plot(rounds, offsets, marker="o", color="#34D399", linewidth=2, markersize=6)
            self.ax_delay.plot(rounds, delays, marker="s", color="#60A5FA", linewidth=2, markersize=6)
        else:
            self.ax_offset.text(0.5, 0.5, "No valid rows", ha="center", va="center", color="#E6F0FA")
            self.ax_delay.text(0.5, 0.5, "No valid rows", ha="center", va="center", color="#E6F0FA")

        self._style_analysis_plot()
        self.figure.tight_layout(pad=1.8)
        self.canvas.draw_idle()

    def _handle_error(self, message: str) -> None:
        self.stop_btn.configure(state="disabled")
        self.status_var.set("Error")
        messagebox.showerror("Sync failed", message)

    def _finish_status(self, message: str) -> None:
        self.stop_btn.configure(state="disabled")
        self.status_var.set(message)

    def _compute_corrected_offset(self) -> float:
        """Compute corrected offset using mean offset from all samples."""
        if not self.rows:
            return 0.0
        offsets = [row.offset for row in self.rows]
        return float(statistics.mean(offsets))

    def _apply_post_sync_correction(self) -> None:
        if not self.rows:
            return

        corrected_offset = self._compute_corrected_offset()
        mean_delay = statistics.mean(row.delay for row in self.rows)
        latest_source = self.rows[-1].time_source

        self.live_offset_seconds = corrected_offset
        self.live_synced = True
        self.server_source_var.set(latest_source)
        self.live_time_status_var.set(
            f"Auto-corrected from {len(self.rows)} rounds (mean delay {mean_delay:.4f}s, mean offset {corrected_offset:.4f}s)"
        )

    def _on_close(self) -> None:
        self.stop_event.set()
        self.destroy()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Client-side GUI for secure clock sync")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--server-hostname", default=None)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL_SECONDS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    app = ClientSyncGUI()
    app.host_var.set(args.host)
    app.port_var.set(str(args.port))
    app.hostname_var.set(args.server_hostname or args.host)
    app.rounds_var.set(str(args.rounds))
    app.interval_var.set(str(args.interval))
    app.mainloop()


if __name__ == "__main__":
    main()
