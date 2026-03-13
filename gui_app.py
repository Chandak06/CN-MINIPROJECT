import csv
import argparse
import os
import queue
import signal
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, messagebox, ttk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen


class ClockSyncGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Distributed Clock Sync Control Center")
        self.geometry("1320x860")
        self.minsize(1080, 720)

        self.processes: dict[str, ManagedProcess] = {}
        self.log_queue: queue.Queue[str] = queue.Queue()

        self._configure_style()
        self._build_layout()

        self.after(120, self._drain_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        bg = "#111827"
        panel = "#1F2937"
        panel_alt = "#243247"
        fg = "#E5E7EB"
        accent = "#22C55E"
        muted = "#9CA3AF"

        self.configure(bg=bg)
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("AltPanel.TFrame", background=panel_alt)
        style.configure("Header.TLabel", background=bg, foreground=fg, font=("Segoe UI Semibold", 16))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 10))
        style.configure("PanelLabel.TLabel", background=panel, foreground=fg, font=("Segoe UI", 10))
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=6)
        style.configure("Primary.TButton", foreground="#0B1B11")
        style.map("Primary.TButton", background=[("!disabled", accent)], foreground=[("!disabled", "#0B1B11")])
        style.configure("StatusGreen.TLabel", background=panel, foreground="#34D399", font=("Segoe UI Semibold", 10))
        style.configure("StatusRed.TLabel", background=panel, foreground="#F87171", font=("Segoe UI Semibold", 10))
        style.configure("TLabelframe", background=panel, foreground=fg)
        style.configure("TLabelframe.Label", background=panel, foreground=fg, font=("Segoe UI Semibold", 10))
        style.configure("TNotebook", background=bg, borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI Semibold", 10), padding=(14, 8))

    def _build_layout(self) -> None:
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True, padx=14, pady=12)

        header = ttk.Frame(root)
        header.pack(fill="x")

        ttk.Label(header, text="Distributed Clock Sync Control Center", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Manage UDP/TLS servers, run synchronized clients, and analyze delay-offset behavior from one interface.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 8))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        self.dashboard_tab = ttk.Frame(notebook)
        self.server_tab = ttk.Frame(notebook)
        self.client_tab = ttk.Frame(notebook)
        self.analysis_tab = ttk.Frame(notebook)

        notebook.add(self.dashboard_tab, text="Dashboard")
        notebook.add(self.server_tab, text="Server Control")
        notebook.add(self.client_tab, text="Client Sync")
        notebook.add(self.analysis_tab, text="Analysis")

        self._build_dashboard_tab()
        self._build_server_tab()
        self._build_client_tab()
        self._build_analysis_tab()

    def _build_dashboard_tab(self) -> None:
        frame = ttk.Frame(self.dashboard_tab, style="Panel.TFrame", padding=14)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        status_row = ttk.Frame(frame, style="Panel.TFrame")
        status_row.pack(fill="x")

        self.udp_status_var = tk.StringVar(value="UDP Server: Stopped")
        self.tls_status_var = tk.StringVar(value="TLS Server: Stopped")
        self.client_status_var = tk.StringVar(value="Client Job: Idle")

        self.udp_status_label = ttk.Label(status_row, textvariable=self.udp_status_var, style="StatusRed.TLabel")
        self.tls_status_label = ttk.Label(status_row, textvariable=self.tls_status_var, style="StatusRed.TLabel")
        self.client_status_label = ttk.Label(status_row, textvariable=self.client_status_var, style="StatusRed.TLabel")

        self.udp_status_label.grid(row=0, column=0, sticky="w", padx=(0, 18), pady=(0, 8))
        self.tls_status_label.grid(row=0, column=1, sticky="w", padx=(0, 18), pady=(0, 8))
        self.client_status_label.grid(row=0, column=2, sticky="w", pady=(0, 8))

        quick_actions = ttk.Frame(frame, style="Panel.TFrame")
        quick_actions.pack(fill="x", pady=(4, 10))

        ttk.Button(quick_actions, text="Start UDP", command=self.start_udp_server).pack(side="left", padx=(0, 8))
        ttk.Button(quick_actions, text="Stop UDP", command=self.stop_udp_server).pack(side="left", padx=(0, 20))
        ttk.Button(quick_actions, text="Start TLS", style="Primary.TButton", command=self.start_tls_server).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(quick_actions, text="Stop TLS", command=self.stop_tls_server).pack(side="left", padx=(0, 20))
        ttk.Button(quick_actions, text="Run Client Sync", style="Primary.TButton", command=self.run_client).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(quick_actions, text="Stop All", command=self.stop_all_processes).pack(side="left")

        ttk.Label(frame, text="Live Logs", style="PanelLabel.TLabel").pack(anchor="w", pady=(4, 4))
        self._build_log_box(frame, panel_style="Panel.TFrame")

    def _build_server_tab(self) -> None:
        outer = ttk.Frame(self.server_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        config_frame = ttk.Frame(outer, style="Panel.TFrame")
        config_frame.pack(fill="x")

        udp_group = ttk.LabelFrame(config_frame, text="UDP Server", padding=12)
        tls_group = ttk.LabelFrame(config_frame, text="TLS Server", padding=12)
        udp_group.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tls_group.grid(row=0, column=1, sticky="nsew")
        config_frame.columnconfigure(0, weight=1)
        config_frame.columnconfigure(1, weight=1)

        self.udp_host_var = tk.StringVar(value="0.0.0.0")
        self.udp_port_var = tk.StringVar(value="5005")
        self.udp_ntp_var = tk.StringVar(value="pool.ntp.org")

        self.tls_host_var = tk.StringVar(value="0.0.0.0")
        self.tls_port_var = tk.StringVar(value="6000")
        self.tls_ntp_var = tk.StringVar(value="pool.ntp.org")

        self._build_labeled_entry(udp_group, "Host", self.udp_host_var, 0)
        self._build_labeled_entry(udp_group, "Port", self.udp_port_var, 1)
        self._build_labeled_entry(udp_group, "NTP Server", self.udp_ntp_var, 2)

        udp_buttons = ttk.Frame(udp_group)
        udp_buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(udp_buttons, text="Start UDP", command=self.start_udp_server).pack(side="left", padx=(0, 8))
        ttk.Button(udp_buttons, text="Stop UDP", command=self.stop_udp_server).pack(side="left")

        self._build_labeled_entry(tls_group, "Host", self.tls_host_var, 0)
        self._build_labeled_entry(tls_group, "Port", self.tls_port_var, 1)
        self._build_labeled_entry(tls_group, "NTP Server", self.tls_ntp_var, 2)

        tls_buttons = ttk.Frame(tls_group)
        tls_buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(tls_buttons, text="Start TLS", style="Primary.TButton", command=self.start_tls_server).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(tls_buttons, text="Stop TLS", command=self.stop_tls_server).pack(side="left")

        ttk.Separator(outer).pack(fill="x", pady=14)
        ttk.Label(outer, text="Server and Process Logs", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 4))
        self._build_log_box(outer, panel_style="Panel.TFrame")

    def _build_client_tab(self) -> None:
        outer = ttk.Frame(self.client_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        client_group = ttk.LabelFrame(outer, text="Secure Client Configuration", padding=12)
        client_group.pack(fill="x")

        self.client_host_var = tk.StringVar(value="127.0.0.1")
        self.client_port_var = tk.StringVar(value="6000")
        self.client_server_hostname_var = tk.StringVar(value="localhost")
        self.client_rounds_var = tk.StringVar(value="10")
        self.client_drift_var = tk.StringVar(value="0.5")
        self.client_output_var = tk.StringVar(value=os.path.join(PROJECT_ROOT, "results", "sync_data.csv"))

        self._build_labeled_entry(client_group, "Server Host", self.client_host_var, 0)
        self._build_labeled_entry(client_group, "Server Port", self.client_port_var, 1)
        self._build_labeled_entry(client_group, "TLS Hostname", self.client_server_hostname_var, 2)
        self._build_labeled_entry(client_group, "Rounds", self.client_rounds_var, 3)
        self._build_labeled_entry(client_group, "Simulated Drift (s)", self.client_drift_var, 4)
        self._build_labeled_entry(client_group, "Output CSV", self.client_output_var, 5)

        row = ttk.Frame(client_group)
        row.grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(row, text="Choose Output", command=self._choose_output_path).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Run Client Sync", style="Primary.TButton", command=self.run_client).pack(side="left", padx=(0, 8))
        ttk.Button(row, text="Stop Client", command=self.stop_client).pack(side="left")

        ttk.Separator(outer).pack(fill="x", pady=14)
        ttk.Label(outer, text="Client Run Logs", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 4))
        self._build_log_box(outer, panel_style="Panel.TFrame")

    def _build_analysis_tab(self) -> None:
        outer = ttk.Frame(self.analysis_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        top = ttk.LabelFrame(outer, text="Analysis Configuration", padding=12)
        top.pack(fill="x")

        self.analysis_input_var = tk.StringVar(value=os.path.join(PROJECT_ROOT, "results", "sync_data.csv"))
        self.analysis_output_var = tk.StringVar(value=os.path.join(PROJECT_ROOT, "results", "sync_plot.png"))

        self._build_labeled_entry(top, "Input CSV", self.analysis_input_var, 0)
        self._build_labeled_entry(top, "Output Plot (optional)", self.analysis_output_var, 1)

        actions = ttk.Frame(top)
        actions.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Choose CSV", command=self._choose_input_csv).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Load CSV", command=self.load_csv_table_and_plot).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Run Drift Estimator", command=self.run_drift_analysis).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Run Accuracy Eval", command=self.run_accuracy_analysis).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Generate Plot File", style="Primary.TButton", command=self.run_plot_script).pack(side="left")

        middle = ttk.Frame(outer, style="Panel.TFrame")
        middle.pack(fill="both", expand=True, pady=(12, 0))
        middle.columnconfigure(0, weight=1)
        middle.columnconfigure(1, weight=1)
        middle.rowconfigure(0, weight=1)

        table_panel = ttk.Frame(middle, style="AltPanel.TFrame", padding=10)
        plot_panel = ttk.Frame(middle, style="AltPanel.TFrame", padding=10)
        table_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        plot_panel.grid(row=0, column=1, sticky="nsew")

        ttk.Label(table_panel, text="Latest Samples", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 6))
        self.tree = ttk.Treeview(table_panel, columns=("round", "offset", "delay", "elapsed"), show="headings", height=15)
        for col, width in (("round", 80), ("offset", 130), ("delay", 130), ("elapsed", 130)):
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=width, anchor="center")

        table_scroll = ttk.Scrollbar(table_panel, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=table_scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        table_scroll.pack(side="right", fill="y")

        ttk.Label(plot_panel, text="Offset and Delay Trend", style="PanelLabel.TLabel").pack(anchor="w", pady=(0, 6))
        self.figure = Figure(figsize=(5.6, 4.2), dpi=100)
        self.ax_offset = self.figure.add_subplot(211)
        self.ax_delay = self.figure.add_subplot(212)
        self.figure.tight_layout(pad=1.8)
        self.canvas = FigureCanvasTkAgg(self.figure, master=plot_panel)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def _build_labeled_entry(self, parent: ttk.Widget, label: str, variable: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 10), pady=5)
        ttk.Entry(parent, textvariable=variable, width=48).grid(row=row, column=1, sticky="ew", pady=5)
        parent.columnconfigure(1, weight=1)

    def _build_log_box(self, parent: ttk.Widget, panel_style: str) -> None:
        wrap = ttk.Frame(parent, style=panel_style)
        wrap.pack(fill="both", expand=True)

        text = tk.Text(
            wrap,
            bg="#0B1220",
            fg="#D1D5DB",
            insertbackground="#D1D5DB",
            relief="flat",
            font=("Consolas", 10),
            wrap="word",
            padx=8,
            pady=8,
            height=14,
        )
        scrollbar = ttk.Scrollbar(wrap, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        if not hasattr(self, "log_boxes"):
            self.log_boxes: list[tk.Text] = []
        self.log_boxes.append(text)

    def _append_log(self, message: str) -> None:
        self.log_queue.put(message.rstrip("\n"))

    def _drain_log_queue(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break

            for box in self.log_boxes:
                box.insert("end", line + "\n")
                box.see("end")

        self.after(120, self._drain_log_queue)

    def _run_subprocess(self, key: str, name: str, args: list[str], persistent: bool = True) -> None:
        if key in self.processes and self.processes[key].process.poll() is None:
            messagebox.showinfo("Already running", f"{name} is already running.")
            return

        command = [sys.executable] + args
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
        if not managed:
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
        self._refresh_status_labels()

    def _refresh_status_labels(self) -> None:
        udp_running = self._is_running("udp_server")
        tls_running = self._is_running("tls_server")
        client_running = self._is_running("client_run")

        self.udp_status_var.set("UDP Server: Running" if udp_running else "UDP Server: Stopped")
        self.tls_status_var.set("TLS Server: Running" if tls_running else "TLS Server: Stopped")
        self.client_status_var.set("Client Job: Running" if client_running else "Client Job: Idle")

        self.udp_status_label.configure(style="StatusGreen.TLabel" if udp_running else "StatusRed.TLabel")
        self.tls_status_label.configure(style="StatusGreen.TLabel" if tls_running else "StatusRed.TLabel")
        self.client_status_label.configure(style="StatusGreen.TLabel" if client_running else "StatusRed.TLabel")

    def _is_running(self, key: str) -> bool:
        managed = self.processes.get(key)
        return bool(managed and managed.process.poll() is None)

    def _validate_port(self, value: str, default: str) -> str | None:
        """Return the port string if valid (1-65535), else show an error and return None."""
        raw = value.strip() or default
        try:
            port = int(raw)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid port", f"Port must be an integer between 1 and 65535 (got: {raw!r}).")
            return None
        return str(port)

    def start_udp_server(self) -> None:
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
            self.udp_ntp_var.get().strip() or "time.google.com",
        ]
        self._run_subprocess("udp_server", "UDP Server", args=args, persistent=True)

    def stop_udp_server(self) -> None:
        self._stop_process("udp_server")

    def start_tls_server(self) -> None:
        cert_path = os.path.join(PROJECT_ROOT, "security", "cert.pem")
        key_path = os.path.join(PROJECT_ROOT, "security", "key.pem")
        if not os.path.exists(cert_path) or not os.path.exists(key_path):
            messagebox.showerror(
                "Missing certificate",
                "TLS certificate/key not found. Run generate_cert.py first.",
            )
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
            self.tls_ntp_var.get().strip() or "time.google.com",
        ]
        self._run_subprocess("tls_server", "TLS Server", args=args, persistent=True)

    def stop_tls_server(self) -> None:
        self._stop_process("tls_server")

    def run_client(self) -> None:
        port = self._validate_port(self.client_port_var.get(), "6000")
        if port is None:
            return

        rounds_raw = self.client_rounds_var.get().strip() or "10"
        try:
            rounds = str(max(1, int(rounds_raw)))
        except ValueError:
            messagebox.showerror("Invalid rounds", f"Rounds must be a positive integer (got: {rounds_raw!r}).")
            return

        output_path = self.client_output_var.get().strip() or os.path.join("results", "sync_data.csv")
        if not output_path.endswith(".csv"):
            messagebox.showerror("Invalid output path", "Output path must end with .csv")
            return

        args = [
            os.path.join("client", "client.py"),
            "--host",
            self.client_host_var.get().strip() or "127.0.0.1",
            "--port",
            port,
            "--server-hostname",
            self.client_server_hostname_var.get().strip() or "localhost",
            "--rounds",
            rounds,
            "--drift",
            self.client_drift_var.get().strip() or "0.5",
            "--output",
            output_path,
        ]
        self._run_subprocess("client_run", "Client", args=args, persistent=False)

    def stop_client(self) -> None:
        self._stop_process("client_run")

    def run_drift_analysis(self) -> None:
        self._run_subprocess(
            key="drift_analysis",
            name="Drift Estimator",
            args=[os.path.join("analysis", "drift_estimator.py"), "--input", self.analysis_input_var.get().strip()],
            persistent=False,
        )

    def run_accuracy_analysis(self) -> None:
        self._run_subprocess(
            key="accuracy_analysis",
            name="Accuracy Evaluator",
            args=[os.path.join("analysis", "accuracy_evaluator.py"), "--input", self.analysis_input_var.get().strip()],
            persistent=False,
        )

    def run_plot_script(self) -> None:
        args = [os.path.join("analysis", "plot_results.py"), "--input", self.analysis_input_var.get().strip()]
        output_path = self.analysis_output_var.get().strip()
        if output_path:
            args += ["--output", output_path]
        self._run_subprocess(key="plot_analysis", name="Plot Generator", args=args, persistent=False)

    def load_csv_table_and_plot(self) -> None:
        csv_path = self.analysis_input_var.get().strip()
        if not csv_path or not os.path.exists(csv_path):
            messagebox.showerror("Missing file", "Input CSV file was not found.")
            return

        rounds: list[float] = []
        offsets: list[float] = []
        delays: list[float] = []

        for item in self.tree.get_children():
            self.tree.delete(item)

        with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                try:
                    round_val = float(row.get("round", 0))
                    offset_val = float(row.get("offset", 0))
                    delay_val = float(row.get("delay", 0))
                    elapsed_val = float(row.get("elapsed", 0))
                except ValueError:
                    continue

                rounds.append(round_val)
                offsets.append(offset_val)
                delays.append(delay_val)
                self.tree.insert(
                    "",
                    "end",
                    values=(f"{round_val:.0f}", f"{offset_val:.6f}", f"{delay_val:.6f}", f"{elapsed_val:.3f}"),
                )

        self.ax_offset.clear()
        self.ax_delay.clear()

        if rounds:
            self.ax_offset.plot(rounds, offsets, marker="o", color="#22D3EE")
            self.ax_offset.set_title("Offset Trend")
            self.ax_offset.set_ylabel("Offset (s)")
            self.ax_offset.grid(alpha=0.3)

            self.ax_delay.plot(rounds, delays, marker="s", color="#F97316")
            self.ax_delay.set_title("Delay Trend")
            self.ax_delay.set_xlabel("Round")
            self.ax_delay.set_ylabel("Delay (s)")
            self.ax_delay.grid(alpha=0.3)
            self._append_log(f"[Analysis] Loaded {len(rounds)} samples from {csv_path}")
        else:
            self.ax_offset.text(0.5, 0.5, "No valid rows", ha="center", va="center")
            self.ax_delay.text(0.5, 0.5, "No valid rows", ha="center", va="center")

        self.figure.tight_layout(pad=1.8)
        self.canvas.draw_idle()

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
            self.client_output_var.set(selected)

    def stop_all_processes(self) -> None:
        for key in list(self.processes.keys()):
            self._stop_process(key)

    def _on_close(self) -> None:
        self.stop_all_processes()
        self.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Tkinter control center for Distributed Clock Sync project")
    parser.add_argument(
        "--version",
        action="version",
        version="Clock Sync GUI 1.0",
        help="Show GUI version and exit",
    )
    parser.parse_args()

    app = ClockSyncGUI()
    app.mainloop()


if __name__ == "__main__":
    main()