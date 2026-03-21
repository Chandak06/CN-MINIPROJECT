# Distributed Clock Synchronization — CN Mini-Project

A modular Python implementation of distributed clock synchronization using an NTP-backed master clock, a custom time-exchange protocol (inspired by IEEE 1588 / NTP), and a Tkinter GUI control center.

---

## Architecture Overview

```
  ┌─────────────────────────────────────────────────────────────────┐
  │                        Master Clock Server                      │
  │  NTP (pool.ntp.org) ──► time_manager.MasterClock               │
  │                              │                                  │
  │               ┌──────────────┼──────────────┐                  │
  │               ▼              ▼               ▼                  │
  │        server.py        secure_server.py                        │
  │       (UDP / port 5005)  (TLS/TCP / port 6000)  ◄── primary    │
  └─────────────────────────────────────────────────────────────────┘
                                 │
              (TLS-encrypted TCP connection)
                                 │
  ┌─────────────────────────────────────────────────────────────────┐
  │                        Secure Client                            │
  │  client/client.py                                               │
  │  1. Send T1 (local timestamp + simulated drift)                 │
  │  2. Receive T2, T3 from server                                  │
  │  3. Record T4 on receipt                                        │
  │  4. Compute offset = ((T2-T1) + (T3-T4)) / 2                   │
  │         delay  = (T4-T1) - (T3-T2)                             │
  │  5. Drift-rate correction via linear regression over rounds     │
  │  6. Write results/sync_data.csv                                 │
  └─────────────────────────────────────────────────────────────────┘
                                 │
              results/sync_data.csv
                                 │
  ┌─────────────────────────────────────────────────────────────────┐
  │                        Analysis Tools                           │
  │  drift_estimator.py   → linear-regression drift rate           │
  │  accuracy_evaluator.py → mean/std offset and delay metrics     │
  │  plot_results.py       → matplotlib offset & delay trend plots │
  └─────────────────────────────────────────────────────────────────┘
```

### UDP vs TLS — What each server does

| Mode | File | Transport | Port | Use case |
|------|------|-----------|------|----------|
| **TLS (primary)** | `server/secure_server.py` | **TCP** with TLS encryption | 6000 | Secure, authenticated time sync; used by `client/client.py` |
| **UDP (alternative)** | `server/server.py` | UDP (unencrypted) | 5005 | Lightweight demo mode; no TLS, no certificate needed |

> **Why TCP for TLS?** TLS requires a reliable, ordered byte stream, which is why the secure server uses TCP (`SOCK_STREAM`) and not UDP (`SOCK_DGRAM`). The extra round-trip overhead is accounted for by the offset/delay calculation (T1–T4 timestamps), which works correctly over any reliable transport.

---

## Project Structure

```
CN-MINIPROJECT/
├── generate_cert.py          # Generate self-signed TLS cert+key
├── gui_app.py                # Tkinter GUI control center
├── requirements.txt
├── results/
│   └── sync_data.csv         # Written by each client run (overwritten each run)
├── security/                 # cert.pem + key.pem (generated, not in VCS)
├── server/
│   ├── server.py             # UDP time-sync server (no TLS)
│   ├── secure_server.py      # TLS/TCP time-sync server (primary)
│   ├── ntp_sync.py           # NTP fetch helper (ntplib)
│   └── time_manager.py       # MasterClock — NTP-backed, thread-safe
├── client/
│   ├── client.py             # Main TLS client (used by GUI)
│   ├── secure_client.py      # Legacy multi-client TLS client
│   ├── sync_algorithm.py     # Offset & delay formulas (T1–T4)
│   └── time_adjuster.py      # corrected_time() helper
├── analysis/
│   ├── drift_estimator.py    # Linear-regression drift rate from CSV
│   ├── accuracy_evaluator.py # Mean/std/min metrics from CSV
│   └── plot_results.py       # Matplotlib offset & delay trend plots
└── utils/
    ├── packet_format.py      # JSON packet builders & validators
    └── statistics_tools.py   # Shared drift + summary statistics
```

---

## Setup

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

> Tkinter is bundled with the standard CPython installer on Windows and macOS.  
> On Linux: `sudo apt install python3-tk`

### 2. Generate TLS certificate (first time only)

```powershell
python generate_cert.py --ips 127.0.0.1 --dns localhost
```

For a LAN deployment, add your server's LAN IP:

```powershell
python generate_cert.py --ips 127.0.0.1 192.168.1.10 --dns localhost myserver
```

This writes `security/cert.pem` and `security/key.pem`.

---

## Running (Command Line)

### Start the TLS server

```powershell
python server/secure_server.py --host 0.0.0.0 --port 6000
```

### Run the client (same machine or LAN)

```powershell
python client/client.py --host 127.0.0.1 --port 6000 --server-hostname localhost --rounds 10 --drift 0.5
```

### Run the client GUI (shows server time received)

```powershell
python client/client_gui.py --host 127.0.0.1 --port 6000 --server-hostname localhost --rounds 10 --drift 0.5
```

In the client GUI, the table column `Server Time (reference_time)` shows the exact server timestamp returned by the TLS server response for each round.

Arguments:

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Server IP |
| `--port` | `6000` | Server port |
| `--server-hostname` | same as `--host` | TLS SNI hostname (must match cert SAN) |
| `--rounds` | `10` | Number of sync rounds |
| `--drift` | `0.5` | Simulated local clock drift in seconds |
| `--output` | `results/sync_data.csv` | CSV output path (overwritten each run) |

### Optional: UDP server (no TLS, demo only)

```powershell
python server/server.py --host 0.0.0.0 --port 5005
```

---

## Running the GUI

```powershell
python gui_app.py
```

Tabs:

| Tab | Purpose |
|-----|---------|
| **Dashboard** | Quick start/stop buttons + live log |
| **Server Control** | Configure and launch UDP or TLS server |
| **Client Sync** | Configure and run the TLS client |
| **Analysis** | Load CSV, view plots, run drift/accuracy scripts |

**Typical workflow:**
1. *Server Control* → Start TLS → confirm green status
2. *Client Sync* → Run Client Sync → watch rounds complete in log
3. *Analysis* → Load CSV → inspect table and inline plot
4. Optionally run Drift Estimator / Accuracy Eval from the Analysis tab

---

## Analysis Tools

```powershell
# Drift rate (linear regression over offset vs elapsed time)
python analysis/drift_estimator.py --input results/sync_data.csv

# Accuracy metrics (mean/std offset and delay)
python analysis/accuracy_evaluator.py --input results/sync_data.csv

# Plot (opens window or saves to file)
python analysis/plot_results.py --input results/sync_data.csv
python analysis/plot_results.py --input results/sync_data.csv --output results/sync_plot.png
```

---

## LAN / Multi-Machine Setup

1. Regenerate the cert on the server machine with its LAN IP in the SAN:
   ```powershell
   python generate_cert.py --ips 127.0.0.1 192.168.1.10 --dns localhost
   ```
2. Copy `security/cert.pem` to every **client** machine (into the same `security/` folder).
3. Run the server on the server machine:
   ```powershell
   python server/secure_server.py --host 0.0.0.0 --port 6000
   ```
4. Run the client on each client machine:
   ```powershell
   python client/client.py --host 192.168.1.10 --port 6000 --server-hostname 192.168.1.10 --rounds 10
   ```

---

## Submission Checklist

- [ ] Remove the `.git/` directory before creating the archive:  
  ```powershell
  Remove-Item -Recurse -Force .git
  ```
- [ ] Create the archive from **inside** the project folder to avoid the nested `CN-MINIPROJECT/CN-MINIPROJECT/` structure:  
  ```powershell
  # From the parent directory:
  Compress-Archive -Path .\CN-MINIPROJECT\* -DestinationPath CN-MINIPROJECT.zip
  ```
- [ ] Verify `security/key.pem` is **not** included (it is a private key — add `security/key.pem` to `.gitignore`).

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `cryptography` | Self-signed TLS certificate generation (`generate_cert.py`) |
| `matplotlib` | Offset/delay trend plots |
| `ntplib` | NTP time fetch for the master clock |
| `tkinter` | GUI (bundled with CPython) |

- Monitor all processes using live logs.
