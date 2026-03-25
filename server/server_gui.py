import csv
import argparse
import json
import os
import queue
import signal
import socket
import ssl
import subprocess
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen


class ClockSyncGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Distributed Clock Sync Server")
        self.geometry("1000x700")
        self.minsize(900, 600)

        self.processes: dict[str, ManagedProcess] = {}
        self.log_queue: queue.Queue[str] = queue.Queue()

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

        ttk.Label(header, text="Distributed Clock Sync Server", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="Manage UDP/TLS servers and monitor server time synchronization.",
            style="Muted.TLabel",
        ).pack(anchor="w", pady=(2, 8))

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        self.dashboard_tab = ttk.Frame(notebook)
        self.server_tab = ttk.Frame(notebook)
        self.live_time_tab = ttk.Frame(notebook)

        notebook.add(self.dashboard_tab, text="Dashboard")
        notebook.add(self.server_tab, text="Server Control")
        notebook.add(self.live_time_tab, text="Live Time")

        self._build_dashboard_tab()
        self._build_server_tab()
        self._build_live_time_tab()

        self.after(120, self._tick_live_time)

    def _build_dashboard_tab(self) -> None:
        frame = ttk.Frame(self.dashboard_tab, style="Panel.TFrame", padding=14)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        status_row = ttk.Frame(frame, style="Panel.TFrame")
        status_row.pack(fill="x")

        self.udp_status_var = tk.StringVar(value="UDP Server: Stopped")
        self.tls_status_var = tk.StringVar(value="TLS Server: Stopped")

        self.udp_status_label = ttk.Label(status_row, textvariable=self.udp_status_var, style="StatusRed.TLabel")
        self.tls_status_label = ttk.Label(status_row, textvariable=self.tls_status_var, style="StatusRed.TLabel")

        self.udp_status_label.grid(row=0, column=0, sticky="w", padx=(0, 18), pady=(0, 8))
        self.tls_status_label.grid(row=0, column=1, sticky="w", padx=(0, 8), pady=(0, 8))

        quick_actions = ttk.Frame(frame, style="Panel.TFrame")
        quick_actions.pack(fill="x", pady=(4, 10))

        ttk.Button(quick_actions, text="Start UDP", command=self.start_udp_server).pack(side="left", padx=(0, 8))
        ttk.Button(quick_actions, text="Stop UDP", command=self.stop_udp_server).pack(side="left", padx=(0, 20))
        ttk.Button(quick_actions, text="Start TLS", style="Primary.TButton", command=self.start_tls_server).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(quick_actions, text="Stop TLS", command=self.stop_tls_server).pack(side="left")

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
        self.udp_ntp_var = tk.StringVar(value="time.google.com")

        self.tls_host_var = tk.StringVar(value="0.0.0.0")
        self.tls_port_var = tk.StringVar(value="6000")
        self.tls_ntp_var = tk.StringVar(value="time.google.com")

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

    def _build_live_time_tab(self) -> None:
        outer = ttk.Frame(self.live_time_tab, style="Panel.TFrame", padding=14)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        cfg = ttk.LabelFrame(outer, text="Server Time Source", padding=12)
        cfg.pack(fill="x")

        self._build_labeled_entry(cfg, "Server Host", self.live_server_host_var, 0)
        self._build_labeled_entry(cfg, "Server Port", self.live_server_port_var, 1)
        self._build_labeled_entry(cfg, "TLS Hostname", self.live_server_hostname_var, 2)

        actions = ttk.Frame(cfg)
        actions.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text="Sync From Server", style="Primary.TButton", command=self.sync_live_time).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(actions, text="Use Local Clock", command=self.reset_live_time_to_local).pack(side="left")

        # Local System Time
        local_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        local_panel.pack(fill="x", pady=(14, 0))
        ttk.Label(local_panel, text="Local System Clock", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(local_panel, textvariable=self.live_local_time_var, style="PanelLabel.TLabel", font=("Consolas", 18, "bold")).grid(
            row=0, column=1, sticky="w"
        )

        # NTP Server Time with Source
        ntp_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        ntp_panel.pack(fill="x", pady=6)
        ttk.Label(ntp_panel, text="NTP Protocol Time (Server Time)", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(ntp_panel, textvariable=self.live_ntp_time_var, style="PanelLabel.TLabel", font=("Consolas", 18, "bold")).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(ntp_panel, text="Sync Source", style="PanelLabel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(8, 0))
        ttk.Label(ntp_panel, textvariable=self.live_ntp_source_var, style="PanelLabel.TLabel").grid(
            row=1, column=1, sticky="w", pady=(8, 0)
        )

        # Time from Querying Server
        synced_panel = ttk.Frame(outer, style="AltPanel.TFrame", padding=16)
        synced_panel.pack(fill="x", pady=(0, 6))
        ttk.Label(synced_panel, text="Server Query Result", style="PanelLabel.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(synced_panel, textvariable=self.live_time_var, style="PanelLabel.TLabel", font=("Consolas", 16)).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Label(synced_panel, text="Status", style="PanelLabel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=(10, 0))
        ttk.Label(synced_panel, textvariable=self.live_time_status_var, style="PanelLabel.TLabel").grid(
            row=1, column=1, sticky="w", pady=(10, 0)
        )

    def _format_clock(self, ts: float) -> str:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

    def _tick_live_time(self) -> None:
        # Display local system time
        local_now = time.time()
        self.live_local_time_var.set(self._format_clock(local_now))
        
        # Display NTP server time (from last successful server query)
        if self.live_synced and self.live_offset_seconds != 0.0:
            ntp_now = local_now + self.live_offset_seconds
            self.live_ntp_time_var.set(self._format_clock(ntp_now))
        else:
            self.live_ntp_time_var.set(self._format_clock(local_now))
        
        # Display combined result
        now = local_now + (self.live_offset_seconds if self.live_synced else 0.0)
        self.live_time_var.set(self._format_clock(now))
        self.after(120, self._tick_live_time)

    def sync_live_time(self) -> None:
        port = self._validate_port(self.live_server_port_var.get(), "6000")
        if port is None:
            return

        host = self.live_server_host_var.get().strip() or "127.0.0.1"
        server_hostname = self.live_server_hostname_var.get().strip() or host
        cert_path = os.path.join(PROJECT_ROOT, "security", "cert.pem")
        if not os.path.exists(cert_path):
            messagebox.showerror("Missing certificate", "security/cert.pem not found. Run generate_cert.py first.")
            return

        self.live_time_status_var.set("Syncing from server...")
        worker = threading.Thread(
            target=self._sync_live_time_worker,
            args=(host, int(port), server_hostname, cert_path),
            daemon=True,
        )
        worker.start()

    def _sync_live_time_worker(self, host: str, port: int, server_hostname: str, cert_path: str) -> None:
        try:
            context = ssl.create_default_context()
            context.load_verify_locations(cert_path)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_socket:
                raw_socket.settimeout(5)
                with context.wrap_socket(raw_socket, server_hostname=server_hostname) as secure_socket:
                    secure_socket.connect((host, port))
                    request_id = int(time.time() * 1000) % 1_000_000
                    t1 = time.time()
                    request = {"type": "TIME_REQUEST", "id": request_id, "T1": t1}
                    secure_socket.sendall(json.dumps(request).encode("utf-8"))
                    response_data = secure_socket.recv(2048)
                    t4 = time.time()

            packet = json.loads(response_data.decode("utf-8"))
            if packet.get("type") != "TIME_REPLY":
                raise ValueError("Invalid reply type from server")
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
        self.live_ntp_source_var.set(str(source))
        self.live_time_status_var.set(f"Synced to server (delay {delay:.4f}s, offset {offset:.4f}s, source {source})")
        self._append_log(f"[Live Time] Updated from server. Delay={delay:.6f}s Offset={offset:.6f}s Source={source}")

    def _on_live_time_sync_error(self, message: str) -> None:
        self.live_time_status_var.set("Sync failed; using local clock")
        messagebox.showerror("Live Time Sync Failed", message)

    def reset_live_time_to_local(self) -> None:
        self.live_ntp_source_var.set("-")
        self.live_synced = False
        self.live_offset_seconds = 0.0
        self.live_time_status_var.set("Using local clock")

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

        # Use unbuffered stdout/stderr so launched process logs appear instantly in the GUI.
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

    def _on_client_run_finished(self, exit_code: int) -> None:
        output_path = self._resolve_project_path(
            self.client_output_var.get().strip(),
            os.path.join("results", "sync_data.csv"),
        )
        self.analysis_input_var.set(output_path)

        if exit_code != 0:
            self._append_log(
                "[Analysis] Client run failed; analysis input was updated, but metrics may still be unavailable until a successful run."
            )
            return

        if os.path.exists(output_path):
            self.load_csv_table_and_plot()
        else:
            self._append_log(f"[Analysis] Latest output CSV not found: {output_path}")

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

        self.udp_status_var.set("UDP Server: Running" if udp_running else "UDP Server: Stopped")
        self.tls_status_var.set("TLS Server: Running" if tls_running else "TLS Server: Stopped")

        self.udp_status_label.configure(style="StatusGreen.TLabel" if udp_running else "StatusRed.TLabel")
        self.tls_status_label.configure(style="StatusGreen.TLabel" if tls_running else "StatusRed.TLabel")

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

    def _resolve_project_path(self, path_value: str, default: str) -> str:
        raw = path_value.strip() or default
        if os.path.isabs(raw):
            return raw
        return os.path.join(PROJECT_ROOT, raw)

    def _wait_for_tcp_port(self, host: str, port: int, timeout_seconds: float = 4.0) -> bool:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            try:
                with socket.create_connection((host, port), timeout=0.5):
                    return True
            except OSError:
                time.sleep(0.15)
        return False

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