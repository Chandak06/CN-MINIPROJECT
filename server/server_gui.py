import argparse
import csv
import json
import os
import queue
import signal
import socket
import ssl
import statistics
import subprocess
import sys
import threading
import time
import tkinter as tk
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERT_FILE = os.path.join(PROJECT_ROOT, "security", "cert.pem")
KEY_FILE = os.path.join(PROJECT_ROOT, "security", "key.pem")
DEFAULT_NTP_SERVER = "pool.ntp.org"


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen


class ClockSyncGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Clock Sync Monitoring Console")
        self.geometry("1320x840")
        self.minsize(1140, 720)

        self.processes: dict[str, ManagedProcess] = {}
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.log_boxes: list[tk.Text] = []

        self.live_local_time_var = tk.StringVar(value="-")
        self.live_ntp_time_var = tk.StringVar(value="-")
        self.live_ntp_source_var = tk.StringVar(value="-")
        self.live_time_var = tk.StringVar(value="-")
        self.live_time_status_var = tk.StringVar(value="Using local clock")
        self.live_server_host_var = tk.StringVar(value="127.0.0.1")
        self.live_server_port_var = tk.StringVar(value="6000")
        self.live_server_hostname_var = tk.StringVar(value="127.0.0.1")
        self.live_offset_seconds = 0.0
        self.live_synced = False

        self.kpi_requests_var = tk.StringVar(value="0")
        self.kpi_errors_var = tk.StringVar(value="0")
        self.kpi_drops_var = tk.StringVar(value="0")
        self.kpi_tls_fail_var = tk.StringVar(value="0")

        self.proof_host_var = tk.StringVar(value="127.0.0.1")
        self.proof_port_var = tk.StringVar(value="6000")
        self.proof_hostname_var = tk.StringVar(value="127.0.0.1")
        self.proof_rounds_var = tk.StringVar(value="20")
        self.proof_interval_var = tk.StringVar(value="0.8")
        self.proof_status_var = tk.StringVar(value="Idle")
        self.proof_latest_var = tk.StringVar(value="No samples yet")

        self.stress_host_var = tk.StringVar(value="127.0.0.1")
        self.stress_port_var = tk.StringVar(value="6000")
        self.stress_hostname_var = tk.StringVar(value="127.0.0.1")
        self.stress_clients_var = tk.StringVar(value="25")
        self.stress_rounds_var = tk.StringVar(value="20")
        self.stress_stagger_var = tk.StringVar(value="10")
        self.stress_output_var = tk.StringVar(value=os.path.join("results", "stress_sync_data.csv"))
        self.stress_status_var = tk.StringVar(value="Idle")
        self.stress_success_var = tk.StringVar(value="-")
        self.stress_throughput_var = tk.StringVar(value="-")
        self.stress_latency_var = tk.StringVar(value="-")

        self.proof_stop_event = threading.Event()
        self.stress_worker: threading.Thread | None = None
        self.proof_worker: threading.Thread | None = None

        self.proof_rounds: deque[int] = deque(maxlen=120)
        self.proof_offsets: deque[float] = deque(maxlen=120)
        self.proof_delays: deque[float] = deque(maxlen=120)
        self.proof_accuracy: deque[float] = deque(maxlen=120)

        self._configure_style()
        self._build_layout()

        self.after(120, self._drain_log_queue)
        self.after(120, self._tick_live_time)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

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
        style.configure("TEntry", fieldbackground="#0B1D30", foreground=fg, insertcolor=fg)
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI Semibold", 10), padding=(14, 8))
        style.configure("Treeview", rowheight=24, fieldbackground="#0B1D30", background="#0B1D30", foreground=fg)
        style.configure("Treeview.Heading", background="#12304D", foreground=fg, font=("Segoe UI Semibold", 10))

    def _build_layout(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=14, pady=12)

        header = ttk.Frame(root)
        header.pack(fill="x")
        ttk.Label(header, text="Distributed Clock Sync Monitoring Console", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Live proof charts, stress simulation, and TLS security intelligence in one place.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=(8, 12))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        self.dashboard_tab = ttk.Frame(notebook)
        self.server_tab = ttk.Frame(notebook)
        self.proof_tab = ttk.Frame(notebook)
        self.stress_tab = ttk.Frame(notebook)
        self.security_tab = ttk.Frame(notebook)
        self.live_time_tab = ttk.Frame(notebook)

        notebook.add(self.dashboard_tab, text="Dashboard")
        notebook.add(self.server_tab, text="Server Control")
        notebook.add(self.proof_tab, text="Visual Proof")
        notebook.add(self.stress_tab, text="Stress Lab")
        notebook.add(self.security_tab, text="Security")
        notebook.add(self.live_time_tab, text="Live Time")

        self._build_dashboard_tab()
        self._build_server_tab()
        self._build_proof_tab()
        self._build_stress_tab()
        self._build_security_tab()
        self._build_live_time_tab()

    def _build_dashboard_tab(self) -> None:
        frame = ttk.Frame(self.dashboard_tab, style="Panel.TFrame", padding=14)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        status_row = ttk.Frame(frame, style="Panel.TFrame")
        status_row.pack(fill="x", pady=(0, 10))

        self.udp_status_var = tk.StringVar(value="UDP Server: Stopped")
        self.tls_status_var = tk.StringVar(value="TLS Server: Stopped")
        self.udp_status_label = ttk.Label(status_row, textvariable=self.udp_status_var, style="StatusRed.TLabel")
        self.tls_status_label = ttk.Label(status_row, textvariable=self.tls_status_var, style="StatusRed.TLabel")

        self.udp_status_label.grid(row=0, column=0, sticky="w", padx=(0, 18))
        self.tls_status_label.grid(row=0, column=1, sticky="w")

        quick = ttk.Frame(frame, style="Panel.TFrame")
        quick.pack(fill="x", pady=(0, 12))
        ttk.Button(quick, text="Start UDP", command=self.start_udp_server).pack(side="left", padx=(0, 8))
        ttk.Button(quick, text="Stop UDP", command=self.stop_udp_server).pack(side="left", padx=(0, 16))
        ttk.Button(quick, text="Start TLS", style="Primary.TButton", command=self.start_tls_server).pack(side="left", padx=(0, 8))
        ttk.Button(quick, text="Stop TLS", command=self.stop_tls_server).pack(side="left")

        cards = ttk.Frame(frame, style="Panel.TFrame")
        cards.pack(fill="x", pady=(0, 12))
        cards.columnconfigure((0, 1, 2, 3), weight=1)
        self._build_kpi_card(cards, "Responses", self.kpi_requests_var, 0)
        self._build_kpi_card(cards, "Errors", self.kpi_errors_var, 1)
        self._build_kpi_card(cards, "Overload Drops", self.kpi_drops_var, 2)
        self._build_kpi_card(cards, "TLS Failures", self.kpi_tls_fail_var, 3)

        ttk.Label(frame, text="Live Logs", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 4))
        self._build_log_box(frame, panel_style="Panel.TFrame")

    def _build_kpi_card(self, parent: ttk.Widget, label: str, value_var: tk.StringVar, column: int) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=12)
        card.grid(row=0, column=column, sticky="nsew", padx=6)
        ttk.Label(card, text=label, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=value_var, style="CardValue.TLabel").pack(anchor="w", pady=(4, 0))

    def _build_server_tab(self) -> None:
        outer = ttk.Frame(self.server_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        config = ttk.Frame(outer, style="Panel.TFrame")
        config.pack(fill="x")
        config.columnconfigure(0, weight=1)
        config.columnconfigure(1, weight=1)

        udp_group = ttk.LabelFrame(config, text="UDP Server", padding=12)
        tls_group = ttk.LabelFrame(config, text="TLS Server", padding=12)
        udp_group.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tls_group.grid(row=0, column=1, sticky="nsew")

        self.udp_host_var = tk.StringVar(value="0.0.0.0")
        self.udp_port_var = tk.StringVar(value="5005")
        self.udp_ntp_var = tk.StringVar(value=DEFAULT_NTP_SERVER)
        self.udp_workers_var = tk.StringVar(value="32")
        self.udp_queue_var = tk.StringVar(value="500")

        self.tls_host_var = tk.StringVar(value="0.0.0.0")
        self.tls_port_var = tk.StringVar(value="6000")
        self.tls_ntp_var = tk.StringVar(value=DEFAULT_NTP_SERVER)
        self.tls_workers_var = tk.StringVar(value="32")
        self.tls_queue_var = tk.StringVar(value="200")
        self.tls_backlog_var = tk.StringVar(value="100")

        self._build_labeled_entry(udp_group, "Host", self.udp_host_var, 0)
        self._build_labeled_entry(udp_group, "Port", self.udp_port_var, 1)
        self._build_labeled_entry(udp_group, "NTP Server", self.udp_ntp_var, 2)
        self._build_labeled_entry(udp_group, "Max Workers", self.udp_workers_var, 3)
        self._build_labeled_entry(udp_group, "Max Queue", self.udp_queue_var, 4)

        udp_buttons = ttk.Frame(udp_group)
        udp_buttons.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(udp_buttons, text="Start UDP", command=self.start_udp_server).pack(side="left", padx=(0, 8))
        ttk.Button(udp_buttons, text="Stop UDP", command=self.stop_udp_server).pack(side="left")

        self._build_labeled_entry(tls_group, "Host", self.tls_host_var, 0)
        self._build_labeled_entry(tls_group, "Port", self.tls_port_var, 1)
        self._build_labeled_entry(tls_group, "NTP Server", self.tls_ntp_var, 2)
        self._build_labeled_entry(tls_group, "Max Workers", self.tls_workers_var, 3)
        self._build_labeled_entry(tls_group, "Max Queue", self.tls_queue_var, 4)
        self._build_labeled_entry(tls_group, "Backlog", self.tls_backlog_var, 5)

        tls_buttons = ttk.Frame(tls_group)
        tls_buttons.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(tls_buttons, text="Start TLS", style="Primary.TButton", command=self.start_tls_server).pack(side="left", padx=(0, 8))
        ttk.Button(tls_buttons, text="Stop TLS", command=self.stop_tls_server).pack(side="left")

        ttk.Separator(outer).pack(fill="x", pady=14)
        ttk.Label(outer, text="Server and Process Logs", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 4))
        self._build_log_box(outer, panel_style="Panel.TFrame")

    def _build_proof_tab(self) -> None:
        outer = ttk.Frame(self.proof_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        cfg = ttk.LabelFrame(outer, text="Proof Session", padding=12)
        cfg.pack(fill="x")
        self._build_labeled_entry(cfg, "Server Host", self.proof_host_var, 0)
        self._build_labeled_entry(cfg, "Server Port", self.proof_port_var, 1)
        self._build_labeled_entry(cfg, "TLS Hostname", self.proof_hostname_var, 2)
        self._build_labeled_entry(cfg, "Rounds", self.proof_rounds_var, 3)
        self._build_labeled_entry(cfg, "Interval (seconds)", self.proof_interval_var, 4)

        actions = ttk.Frame(cfg)
        actions.grid(row=5, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.proof_start_btn = ttk.Button(actions, text="Start Proof Capture", style="Primary.TButton", command=self.start_proof_capture)
        self.proof_stop_btn = ttk.Button(actions, text="Stop", command=self.stop_proof_capture, state="disabled")
        self.proof_clear_btn = ttk.Button(actions, text="Clear Charts", command=self.clear_proof_data)
        self.proof_start_btn.pack(side="left", padx=(0, 8))
        self.proof_stop_btn.pack(side="left", padx=(0, 8))
        self.proof_clear_btn.pack(side="left")

        ttk.Label(outer, textvariable=self.proof_status_var, style="PanelLabel.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(outer, textvariable=self.proof_latest_var, style="PanelLabel.TLabel").pack(anchor="w", pady=(2, 10))

        self.proof_figure = Figure(figsize=(9.4, 5.0), dpi=100)
        self.proof_figure.set_facecolor("#10243A")
        self.proof_ax_offset = self.proof_figure.add_subplot(311)
        self.proof_ax_delay = self.proof_figure.add_subplot(312)
        self.proof_ax_accuracy = self.proof_figure.add_subplot(313)
        self.proof_canvas = FigureCanvasTkAgg(self.proof_figure, master=outer)
        self.proof_canvas.get_tk_widget().configure(bg="#10243A", highlightthickness=0)
        self.proof_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._redraw_proof_plot()

    def _build_stress_tab(self) -> None:
        outer = ttk.Frame(self.stress_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        cfg = ttk.LabelFrame(outer, text="Multi-Client Stress Simulation", padding=12)
        cfg.pack(fill="x")
        self._build_labeled_entry(cfg, "Server Host", self.stress_host_var, 0)
        self._build_labeled_entry(cfg, "Server Port", self.stress_port_var, 1)
        self._build_labeled_entry(cfg, "TLS Hostname", self.stress_hostname_var, 2)
        self._build_labeled_entry(cfg, "Concurrent Clients", self.stress_clients_var, 3)
        self._build_labeled_entry(cfg, "Rounds per Client", self.stress_rounds_var, 4)
        self._build_labeled_entry(cfg, "Launch Stagger (ms)", self.stress_stagger_var, 5)
        self._build_labeled_entry(cfg, "Output CSV", self.stress_output_var, 6)

        actions = ttk.Frame(cfg)
        actions.grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.stress_start_btn = ttk.Button(actions, text="Run Stress Test", style="Primary.TButton", command=self.start_stress_test)
        self.stress_csv_btn = ttk.Button(actions, text="Choose CSV", command=self.choose_stress_output)
        self.stress_start_btn.pack(side="left", padx=(0, 8))
        self.stress_csv_btn.pack(side="left")

        metrics = ttk.Frame(outer, style="Panel.TFrame")
        metrics.pack(fill="x", pady=(12, 10))
        metrics.columnconfigure((0, 1, 2), weight=1)
        self._build_kpi_card(metrics, "Success Rate", self.stress_success_var, 0)
        self._build_kpi_card(metrics, "Throughput", self.stress_throughput_var, 1)
        self._build_kpi_card(metrics, "Mean Delay", self.stress_latency_var, 2)

        ttk.Label(outer, textvariable=self.stress_status_var, style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 6))
        self._build_log_box(outer, panel_style="Panel.TFrame")

    def _build_security_tab(self) -> None:
        outer = ttk.Frame(self.security_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        top = ttk.Frame(outer, style="Panel.TFrame")
        top.pack(fill="x", pady=(0, 10))

        ttk.Label(top, text="Why TLS matters", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            top,
            text=(
                "TLS gives authenticity, confidentiality, and integrity to clock packets. "
                "Without TLS, an attacker can alter timestamps and poison offset calculations."
            ),
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        table = ttk.Treeview(outer, columns=("area", "udp_mode", "tls_mode"), show="headings", height=7)
        table.heading("area", text="Area")
        table.heading("udp_mode", text="UDP (insecure)")
        table.heading("tls_mode", text="TLS/TCP (secure)")
        table.column("area", width=190, anchor="w")
        table.column("udp_mode", width=360, anchor="w")
        table.column("tls_mode", width=360, anchor="w")
        table.pack(fill="x", pady=(0, 10))

        rows = [
            ("Authentication", "No server identity proof", "Certificate-backed server identity"),
            ("Tampering", "Packets can be modified in transit", "Integrity checks reject modified packets"),
            ("Spoofing", "Fake server can reply with forged time", "Hostname plus cert validation blocks spoof server"),
            ("Confidentiality", "Timestamps visible to observers", "Encrypted session hides traffic"),
            ("MITM impact", "High: attacker can inject wrong time", "Low: handshake fails without trusted cert"),
            ("Operational advice", "Use only for trusted lab LAN", "Use for production or evaluation demos"),
        ]
        for row in rows:
            table.insert("", "end", values=row)

        attacks = tk.Text(
            outer,
            bg="#0B1D30",
            fg="#E6F0FA",
            insertbackground="#E6F0FA",
            relief="flat",
            font=("Consolas", 10),
            wrap="word",
            height=12,
            padx=8,
            pady=8,
        )
        attacks.pack(fill="both", expand=True)
        attacks.insert(
            "end",
            "Attack scenario checklist:\n\n"
            "1) Replay attack:\n"
            "   In insecure mode, an attacker replays old TIME_REPLY packets causing stale offsets.\n"
            "   In TLS mode, authenticated sessions reduce replay feasibility.\n\n"
            "2) On-path manipulation:\n"
            "   Without TLS, attacker modifies T2/T3 and inflates drift estimates.\n"
            "   TLS integrity checks make modified packets fail.\n\n"
            "3) Rogue time server:\n"
            "   In UDP mode, client may trust a forged responder.\n"
            "   In TLS mode, client verifies certificate SAN and trust chain before accepting data.\n\n"
            "Use this tab in demos to explain security tradeoffs instead of showing TLS as a checkbox feature.\n",
        )
        attacks.configure(state="disabled")

    def _build_live_time_tab(self) -> None:
        outer = ttk.Frame(self.live_time_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        cfg = ttk.LabelFrame(outer, text="Live Server Time", padding=12)
        cfg.pack(fill="x")

        self._build_labeled_entry(cfg, "Server Host", self.live_server_host_var, 0)
        self._build_labeled_entry(cfg, "Server Port", self.live_server_port_var, 1)
        self._build_labeled_entry(cfg, "TLS Hostname", self.live_server_hostname_var, 2)

        actions = ttk.Frame(cfg)
        actions.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Sync From Server", style="Primary.TButton", command=self.sync_live_time).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Use Local Clock", command=self.reset_live_time_to_local).pack(side="left")

        local_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        local_panel.pack(fill="x", pady=(12, 0))
        ttk.Label(local_panel, text="Local Clock", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(local_panel, textvariable=self.live_local_time_var, style="PanelLabel.TLabel", font=("Consolas", 18, "bold")).grid(row=0, column=1, sticky="w")

        ntp_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        ntp_panel.pack(fill="x", pady=6)
        ttk.Label(ntp_panel, text="NTP Server Time", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(ntp_panel, textvariable=self.live_ntp_time_var, style="PanelLabel.TLabel", font=("Consolas", 18, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(ntp_panel, text="Source", style="PanelLabel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(8, 0))
        ttk.Label(ntp_panel, textvariable=self.live_ntp_source_var, style="PanelLabel.TLabel").grid(row=1, column=1, sticky="w", pady=(8, 0))

        synced_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        synced_panel.pack(fill="x", pady=(0, 6))
        ttk.Label(synced_panel, text="Corrected Time", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(synced_panel, textvariable=self.live_time_var, style="PanelLabel.TLabel", font=("Consolas", 18, "bold")).grid(row=0, column=1, sticky="w")
        ttk.Label(synced_panel, text="Status", style="PanelLabel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(8, 0))
        ttk.Label(synced_panel, textvariable=self.live_time_status_var, style="PanelLabel.TLabel").grid(row=1, column=1, sticky="w", pady=(8, 0))

    def _build_log_box(self, parent: ttk.Widget, panel_style: str = "Panel.TFrame") -> None:
        """Build a log text box with scrollbar and add to log_boxes list."""
        log_frame = ttk.Frame(parent, style=panel_style)
        log_frame.pack(fill="both", expand=True, pady=(6, 0))

        log_text = tk.Text(
            log_frame,
            bg="#0B1D30",
            fg="#E6F0FA",
            insertbackground="#E6F0FA",
            relief="flat",
            font=("Consolas", 9),
            wrap="word",
            height=8,
            padx=8,
            pady=8,
        )
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=log_text.yview)
        log_text.configure(yscrollcommand=scrollbar.set)

        log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.log_boxes.append(log_text)

    def _build_labeled_entry(self, parent: ttk.Widget, label: str, var: tk.StringVar, row: int) -> None:
        """Build a labeled entry field in a grid layout."""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=6)
        ttk.Entry(parent, textvariable=var, width=48).grid(row=row, column=1, sticky="ew", pady=6)
        parent.columnconfigure(1, weight=1)

    def _append_log(self, message: str) -> None:
        self.log_queue.put(message.rstrip("\n"))

    def _increment_counter(self, counter_var: tk.StringVar, amount: int = 1) -> None:
        try:
            current = int(counter_var.get())
        except (TypeError, ValueError):
            current = 0
        counter_var.set(str(current + amount))

    def _record_tls_client_failure(self, context: str, message: str) -> None:
        self._increment_counter(self.kpi_tls_fail_var)
        self._append_log(f"{context}: {message}")

    def _is_stress_tls_failure_line(self, line: str) -> bool:
        stripped = line.strip()
        if stripped.startswith("[Stress] ERROR:"):
            return True
        if not stripped.startswith("[Stress] Client "):
            return False

        lowered = stripped.lower()
        error_tokens = (
            "[winerror",
            "[errno",
            "refused",
            "timed out",
            "ssl",
            "certificate",
            "eof",
            "network error",
        )
        return any(token in lowered for token in error_tokens)

    def _drain_log_queue(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break

            self._ingest_log_line(line)
            for box in self.log_boxes:
                box.insert("end", line + "\n")
                box.see("end")

        self.after(120, self._drain_log_queue)

    def _ingest_log_line(self, line: str) -> None:
        if "Responded to" in line:
            self._increment_counter(self.kpi_requests_var)
        if "Client error" in line or "Error handling request" in line:
            self._increment_counter(self.kpi_errors_var)
        if "Overloaded, dropping" in line:
            self._increment_counter(self.kpi_drops_var)
        if "TLS handshake failed for" in line or self._is_stress_tls_failure_line(line):
            self._increment_counter(self.kpi_tls_fail_var)

    def _run_subprocess(self, key: str, name: str, args: list[str], persistent: bool = True) -> None:
        if key in self.processes and self.processes[key].process.poll() is None:
            messagebox.showinfo("Already running", f"{name} is already running.")
            return

        command = [sys.executable, "-u"] + args
        self._append_log(f"[Launcher] Starting {name}: {' '.join(command)}")

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creation_flags,
        )
        self.processes[key] = ManagedProcess(name=name, process=process)

        watcher = threading.Thread(target=self._stream_process_output, args=(key, persistent), daemon=True)
        watcher.start()
        self._refresh_status_labels()

    def _stream_process_output(self, key: str, persistent: bool) -> None:
        managed = self.processes.get(key)
        if not managed:
            return
        proc = managed.process

        if proc.stdout is not None:
            for line in proc.stdout:
                self._append_log(f"[{managed.name}] {line.rstrip()}")

        code = proc.wait()
        self._append_log(f"[{managed.name}] Exited with code {code}")

        if not persistent:
            self.processes.pop(key, None)
        self._refresh_status_labels()

    def _stop_process(self, key: str) -> None:
        managed = self.processes.get(key)
        if key == "udp_server":
            port = self._parse_positive_int(self.udp_port_var.get().strip(), 5005)
            proto = "udp"
        else:
            port = self._parse_positive_int(self.tls_port_var.get().strip(), 6000)
            proto = "tcp"

        if not managed:
            # Still try to stop external listeners (e.g., servers started from another terminal).
            stopped = self._stop_external_listeners(port=port, proto=proto)
            if stopped:
                self._append_log(f"[Launcher] Stopped external listeners on {proto.upper()} port {port}.")
            self._refresh_status_labels()
            return

        proc = managed.process
        if proc.poll() is not None:
            return

        self._append_log(f"[Launcher] Stopping {managed.name}...")
        try:
            if os.name == "nt":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.terminate()
        except Exception:
            proc.terminate()

        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)

        self._append_log(f"[Launcher] {managed.name} stopped.")
        self.processes.pop(key, None)
        # Ensure no stale external process is still bound to the expected port.
        self._stop_external_listeners(port=port, proto=proto)
        self._refresh_status_labels()

    def _find_listening_pids(self, port: int, proto: str) -> list[int]:
        """Find listener PIDs for a port using netstat on Windows."""
        try:
            result = subprocess.run(
                ["netstat", "-ano", "-p", proto],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return []

        pids: set[int] = set()
        needle = f":{port}"
        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if needle not in line:
                continue

            parts = line.split()
            if proto == "tcp":
                # Expected: TCP local_addr foreign_addr LISTENING pid
                if len(parts) < 5 or parts[0].upper() != "TCP" or parts[3].upper() != "LISTENING":
                    continue
                pid_str = parts[4]
            else:
                # Expected: UDP local_addr foreign_addr pid
                if len(parts) < 4 or parts[0].upper() != "UDP":
                    continue
                pid_str = parts[3]

            try:
                pid = int(pid_str)
            except ValueError:
                continue

            if pid > 0 and pid != os.getpid():
                pids.add(pid)

        return sorted(pids)

    def _stop_external_listeners(self, port: int, proto: str) -> bool:
        """Force-stop processes listening on a specific port."""
        stopped_any = False
        for pid in self._find_listening_pids(port=port, proto=proto):
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True, check=False)
                stopped_any = True
            except OSError:
                continue
        return stopped_any

    def _refresh_status_labels(self) -> None:
        udp_running = self._is_running("udp_server")
        tls_running = self._is_running("tls_server")
        self.udp_status_var.set("UDP Server: Running" if udp_running else "UDP Server: Stopped")
        self.tls_status_var.set("TLS Server: Running" if tls_running else "TLS Server: Stopped")
        self.udp_status_label.configure(style="StatusGreen.TLabel" if udp_running else "StatusRed.TLabel")
        self.tls_status_label.configure(style="StatusGreen.TLabel" if tls_running else "StatusRed.TLabel")

    def _is_running(self, key: str) -> bool:
        managed = self.processes.get(key)
        return bool(managed and managed.process.poll() is None)

    def _validate_port(self, value: str, default: str) -> str | None:
        raw = value.strip() or default
        try:
            port = int(raw)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid port", f"Port must be an integer between 1 and 65535 (got: {raw!r}).")
            return None
        return str(port)

    def _resolve_project_path(self, path_value: str, default: str) -> str:
        raw = path_value.strip() or default
        if os.path.isabs(raw):
            return raw
        return os.path.join(PROJECT_ROOT, raw)

    def _parse_positive_int(self, raw: str, fallback: int) -> int:
        try:
            value = int(raw)
            return max(1, value)
        except ValueError:
            return fallback

    def _format_clock(self, ts: float) -> str:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _tick_live_time(self) -> None:
        local_now = time.time()
        self.live_local_time_var.set(self._format_clock(local_now))

        if self.live_synced and self.live_offset_seconds != 0.0:
            ntp_now = local_now + self.live_offset_seconds
            self.live_ntp_time_var.set(self._format_clock(ntp_now))
        else:
            self.live_ntp_time_var.set(self._format_clock(local_now))

        self.live_time_var.set(self._format_clock(local_now + (self.live_offset_seconds if self.live_synced else 0.0)))
        self.after(120, self._tick_live_time)

    def sync_live_time(self) -> None:
        port = self._validate_port(self.live_server_port_var.get(), "6000")
        if port is None:
            return

        host = self.live_server_host_var.get().strip() or "127.0.0.1"
        server_hostname = self.live_server_hostname_var.get().strip() or host
        if not os.path.exists(CERT_FILE):
            messagebox.showerror("Missing certificate", "security/cert.pem not found. Run generate_cert.py first.")
            return

        self.live_time_status_var.set("Syncing from server...")
        worker = threading.Thread(target=self._sync_live_time_worker, args=(host, int(port), server_hostname), daemon=True)
        worker.start()

    def _sync_live_time_worker(self, host: str, port: int, server_hostname: str) -> None:
        try:
            context = ssl.create_default_context()
            context.load_verify_locations(CERT_FILE)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_socket:
                raw_socket.settimeout(5)
                with context.wrap_socket(raw_socket, server_hostname=server_hostname) as secure_socket:
                    secure_socket.connect((host, port))
                    request_id = int(time.time() * 1000) % 1_000_000
                    t1 = time.time()
                    secure_socket.sendall(json.dumps({"type": "TIME_REQUEST", "id": request_id, "T1": t1}).encode("utf-8"))
                    response_data = secure_socket.recv(2048)
                    t4 = time.time()

            packet = json.loads(response_data.decode("utf-8"))
            if packet.get("type") != "TIME_REPLY":
                raise ValueError("Invalid reply type")
            if int(packet.get("id", -1)) != request_id:
                raise ValueError("Mismatched response id")

            t2 = float(packet["T2"])
            t3 = float(packet["T3"])
            offset = ((t2 - t1) + (t3 - t4)) / 2.0
            delay = (t4 - t1) - (t3 - t2)
            source = str(packet.get("time_source", "unknown"))
            self.after(0, self._on_live_time_synced, offset, delay, source)
        except Exception as exc:
            self.after(0, self._on_live_time_sync_error, str(exc))

    def _on_live_time_synced(self, offset: float, delay: float, source: str) -> None:
        self.live_offset_seconds = offset
        self.live_synced = True
        self.live_ntp_source_var.set(source)
        self.live_time_status_var.set(f"Synced to server (delay {delay:.4f}s, offset {offset:.4f}s, source {source})")
        self._append_log(f"[Live Time] Delay={delay:.6f}s Offset={offset:.6f}s Source={source}")

    def _on_live_time_sync_error(self, message: str) -> None:
        self.live_time_status_var.set("Sync failed; using local clock")
        self._record_tls_client_failure("[Live Time] TLS sync failed", message)
        messagebox.showerror("Live Time Sync Failed", message)

    def reset_live_time_to_local(self) -> None:
        self.live_ntp_source_var.set("-")
        self.live_synced = False
        self.live_offset_seconds = 0.0
        self.live_time_status_var.set("Using local clock")

    def start_proof_capture(self) -> None:
        if self.proof_worker and self.proof_worker.is_alive():
            return

        if not os.path.exists(CERT_FILE):
            messagebox.showerror("Missing certificate", "security/cert.pem not found. Run generate_cert.py first.")
            return

        port = self._validate_port(self.proof_port_var.get(), "6000")
        if port is None:
            return

        host = self.proof_host_var.get().strip() or "127.0.0.1"
        hostname = self.proof_hostname_var.get().strip() or host
        rounds = self._parse_positive_int(self.proof_rounds_var.get().strip(), 20)
        try:
            interval = max(0.1, float(self.proof_interval_var.get().strip()))
        except ValueError:
            interval = 0.8

        self.proof_stop_event.clear()
        self.proof_status_var.set("Running proof capture...")
        self.proof_start_btn.configure(state="disabled")
        self.proof_stop_btn.configure(state="normal")

        self.proof_worker = threading.Thread(
            target=self._proof_worker_loop,
            args=(host, int(port), hostname, rounds, interval),
            daemon=True,
        )
        self.proof_worker.start()

    def stop_proof_capture(self) -> None:
        self.proof_stop_event.set()
        self.proof_status_var.set("Stopping proof capture...")

    def clear_proof_data(self) -> None:
        self.proof_rounds.clear()
        self.proof_offsets.clear()
        self.proof_delays.clear()
        self.proof_accuracy.clear()
        self.proof_latest_var.set("No samples yet")
        self._redraw_proof_plot()

    def _proof_worker_loop(self, host: str, port: int, hostname: str, rounds: int, interval: float) -> None:
        context = ssl.create_default_context()
        context.load_verify_locations(CERT_FILE)

        for round_id in range(1, rounds + 1):
            if self.proof_stop_event.is_set():
                break
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_socket:
                    raw_socket.settimeout(5)
                    with context.wrap_socket(raw_socket, server_hostname=hostname) as secure_socket:
                        secure_socket.connect((host, port))
                        request_id = int(time.time() * 1000) % 1_000_000
                        t1 = time.time()
                        secure_socket.sendall(json.dumps({"type": "TIME_REQUEST", "id": request_id, "T1": t1}).encode("utf-8"))
                        response_data = secure_socket.recv(2048)
                        t4 = time.time()

                packet = json.loads(response_data.decode("utf-8"))
                if packet.get("type") != "TIME_REPLY" or int(packet.get("id", -1)) != request_id:
                    raise ValueError("Invalid TIME_REPLY")

                t2 = float(packet["T2"])
                t3 = float(packet["T3"])
                reference = float(packet.get("reference_time", t4))
                offset = ((t2 - t1) + (t3 - t4)) / 2.0
                delay = (t4 - t1) - (t3 - t2)
                corrected_error = abs((t4 + offset) - reference)

                self.after(0, self._append_proof_sample, round_id, offset, delay, corrected_error)
            except Exception as exc:
                self.after(0, self._on_proof_round_failed, round_id, str(exc))

            slept = 0.0
            while slept < interval and not self.proof_stop_event.is_set():
                step = min(0.1, interval - slept)
                time.sleep(step)
                slept += step

        self.after(0, self._proof_finished)

    def _append_proof_sample(self, round_id: int, offset: float, delay: float, corrected_error: float) -> None:
        self.proof_rounds.append(round_id)
        self.proof_offsets.append(offset)
        self.proof_delays.append(delay)
        self.proof_accuracy.append(corrected_error)
        self.proof_latest_var.set(
            f"Latest round {round_id}: offset={offset:.6f}s delay={delay:.6f}s corrected_error={corrected_error:.6f}s"
        )
        self._redraw_proof_plot()

    def _on_proof_round_failed(self, round_id: int, message: str) -> None:
        self._record_tls_client_failure(f"[Proof] Round {round_id} failed", message)

    def _proof_finished(self) -> None:
        if self.proof_stop_event.is_set():
            self.proof_status_var.set("Proof capture stopped")
        else:
            self.proof_status_var.set("Proof capture completed")
        self.proof_start_btn.configure(state="normal")
        self.proof_stop_btn.configure(state="disabled")

    def _redraw_proof_plot(self) -> None:
        axes = [self.proof_ax_offset, self.proof_ax_delay, self.proof_ax_accuracy]
        for ax in axes:
            ax.clear()
            ax.set_facecolor("#0B1D30")
            ax.tick_params(axis="both", colors="#E6F0FA", labelcolor="#E6F0FA")
            ax.grid(alpha=0.25, color="#4A6D90")
            for spine in ax.spines.values():
                spine.set_color("#55799D")

        rounds = list(self.proof_rounds)
        if rounds:
            self.proof_ax_offset.plot(rounds, list(self.proof_offsets), marker="o", color="#34D399")
            self.proof_ax_delay.plot(rounds, list(self.proof_delays), marker="s", color="#60A5FA")
            self.proof_ax_accuracy.plot(rounds, list(self.proof_accuracy), marker="^", color="#F59E0B")

        self.proof_ax_offset.set_title("Clock Drift Proxy: Offset Over Rounds", color="#E6F0FA")
        self.proof_ax_offset.set_ylabel("Offset (s)", color="#E6F0FA")
        self.proof_ax_delay.set_title("Delay Trend", color="#E6F0FA")
        self.proof_ax_delay.set_ylabel("Delay (s)", color="#E6F0FA")
        self.proof_ax_accuracy.set_title("Sync Accuracy Over Time", color="#E6F0FA")
        self.proof_ax_accuracy.set_ylabel("Corrected Error (s)", color="#E6F0FA")
        self.proof_ax_accuracy.set_xlabel("Round", color="#E6F0FA")

        self.proof_figure.patch.set_facecolor("#10243A")
        self.proof_figure.tight_layout(pad=1.5)
        self.proof_canvas.draw_idle()

    def choose_stress_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Select stress output CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialdir=os.path.join(PROJECT_ROOT, "results"),
        )
        if path:
            self.stress_output_var.set(path)

    def start_stress_test(self) -> None:
        if self.stress_worker and self.stress_worker.is_alive():
            return

        port = self._validate_port(self.stress_port_var.get(), "6000")
        if port is None:
            return

        host = self.stress_host_var.get().strip() or "127.0.0.1"
        hostname = self.stress_hostname_var.get().strip() or host
        clients = self._parse_positive_int(self.stress_clients_var.get().strip(), 25)
        rounds = self._parse_positive_int(self.stress_rounds_var.get().strip(), 20)
        stagger = self._parse_positive_int(self.stress_stagger_var.get().strip(), 10)
        output_csv = self._resolve_project_path(self.stress_output_var.get().strip(), os.path.join("results", "stress_sync_data.csv"))

        self.stress_status_var.set("Running stress test...")
        self.stress_start_btn.configure(state="disabled")
        self.stress_worker = threading.Thread(
            target=self._run_stress_worker,
            args=(host, int(port), hostname, clients, rounds, stagger, output_csv),
            daemon=True,
        )
        self.stress_worker.start()

    def _run_stress_worker(
        self,
        host: str,
        port: int,
        hostname: str,
        clients: int,
        rounds: int,
        stagger: int,
        output_csv: str,
    ) -> None:
        command = [
            sys.executable,
            "-u",
            os.path.join("client", "client.py"),
            "--host",
            host,
            "--port",
            str(port),
            "--server-hostname",
            hostname,
            "--rounds",
            str(rounds),
            "--clients",
            str(clients),
            "--stagger-ms",
            str(stagger),
            "--output",
            output_csv,
        ]
        self._append_log(f"[Stress] Running: {' '.join(command)}")

        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        start = time.perf_counter()
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creation_flags,
        )

        if process.stdout is not None:
            for line in process.stdout:
                self._append_log(f"[Stress] {line.rstrip()}")

        code = process.wait()
        duration = max(0.001, time.perf_counter() - start)
        self.after(0, self._finish_stress_test, code, clients, rounds, output_csv, duration)

    def _finish_stress_test(self, code: int, clients: int, rounds: int, output_csv: str, duration: float) -> None:
        self.stress_start_btn.configure(state="normal")
        if code != 0:
            self.stress_status_var.set(f"Stress test failed (exit code {code})")
            return

        metrics = self._compute_stress_metrics(output_csv, clients, rounds, duration)
        self.stress_status_var.set("Stress test completed")
        self.stress_success_var.set(f"{metrics['success_rate']:.1f}%")
        self.stress_throughput_var.set(f"{metrics['throughput']:.2f} samples/s")
        self.stress_latency_var.set(f"{metrics['mean_delay']:.6f}s")

    def _compute_stress_metrics(self, csv_path: str, clients: int, rounds: int, duration: float) -> dict[str, float]:
        total_target = max(1, clients * rounds)
        rows: list[dict[str, str]] = []
        if os.path.exists(csv_path):
            with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    rows.append(row)

        total_samples = len(rows)
        delays = []
        for row in rows:
            try:
                delays.append(float(row.get("delay", "0")))
            except ValueError:
                continue

        success_rate = (total_samples / total_target) * 100.0
        throughput = total_samples / max(duration, 0.001)
        mean_delay = statistics.mean(delays) if delays else 0.0

        self._append_log(
            f"[Stress] Metrics: samples={total_samples}/{total_target}, success={success_rate:.2f}%, throughput={throughput:.2f}/s, mean_delay={mean_delay:.6f}s"
        )

        return {
            "success_rate": success_rate,
            "throughput": throughput,
            "mean_delay": mean_delay,
        }

    def start_udp_server(self) -> None:
        desired_port = self._parse_positive_int(self.udp_port_var.get().strip(), 5005)
        if self._find_listening_pids(port=desired_port, proto="udp"):
            messagebox.showwarning(
                "UDP port busy",
                f"UDP port {desired_port} is already in use. Stop the existing UDP server first.",
            )
            return

        port = self._validate_port(self.udp_port_var.get(), "5005")
        if port is None:
            return

        args = [
            os.path.join("server", "server.py"),
            "--host",
            self.udp_host_var.get().strip() or "0.0.0.0",
            "--port",
            port,
            "--ntp-server",
            self.udp_ntp_var.get().strip() or DEFAULT_NTP_SERVER,
            "--max-workers",
            str(self._parse_positive_int(self.udp_workers_var.get().strip(), 32)),
            "--max-queue",
            str(self._parse_positive_int(self.udp_queue_var.get().strip(), 500)),
        ]
        self._run_subprocess("udp_server", "UDP Server", args=args, persistent=True)

    def stop_udp_server(self) -> None:
        self._stop_process("udp_server")

    def start_tls_server(self) -> None:
        desired_port = self._parse_positive_int(self.tls_port_var.get().strip(), 6000)
        if self._find_listening_pids(port=desired_port, proto="tcp"):
            messagebox.showwarning(
                "TLS port busy",
                f"TCP port {desired_port} is already in use. Stop the existing TLS server first.",
            )
            return

        if not os.path.exists(CERT_FILE) or not os.path.exists(KEY_FILE):
            messagebox.showerror("Missing certificate", "TLS certificate/key not found. Run generate_cert.py first.")
            return

        port = self._validate_port(self.tls_port_var.get(), "6000")
        if port is None:
            return

        args = [
            os.path.join("server", "secure_server.py"),
            "--host",
            self.tls_host_var.get().strip() or "0.0.0.0",
            "--port",
            port,
            "--ntp-server",
            self.tls_ntp_var.get().strip() or DEFAULT_NTP_SERVER,
            "--max-workers",
            str(self._parse_positive_int(self.tls_workers_var.get().strip(), 32)),
            "--max-queue",
            str(self._parse_positive_int(self.tls_queue_var.get().strip(), 200)),
            "--backlog",
            str(self._parse_positive_int(self.tls_backlog_var.get().strip(), 100)),
        ]
        self._run_subprocess("tls_server", "TLS Server", args=args, persistent=True)

    def stop_tls_server(self) -> None:
        self._stop_process("tls_server")

    def stop_all_processes(self) -> None:
        for key in list(self.processes.keys()):
            self._stop_process(key)

    def _on_close(self) -> None:
        self.proof_stop_event.set()
        self.stop_all_processes()
        self.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitoring GUI for Distributed Clock Sync")
    parser.add_argument("--version", action="version", version="Clock Sync GUI 2.0")
    parser.parse_args()

    app = ClockSyncGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
