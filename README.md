# Distributed Clock Sync (Secure + Analysis)

This project implements a modular distributed clock synchronization system with:
- Master server time management synced to NTP (`pool.ntp.org` by default)
- UDP and secure TLS server modes
- Secure client synchronization rounds with offset/delay calculation
- Drift correction and accuracy evaluation
- CSV export and plotting tools

## Project Structure

- `server/server.py`: UDP synchronization server
- `server/secure_server.py`: TLS synchronization server
- `server/ntp_sync.py`: NTP fetch helper
- `server/time_manager.py`: Master clock manager with periodic sync
- `client/client.py`: Secure synchronization client
- `client/sync_algorithm.py`: Offset and delay formulas
- `client/time_adjuster.py`: Local time correction helpers
- `analysis/drift_estimator.py`: Drift-rate estimation from CSV
- `analysis/accuracy_evaluator.py`: Accuracy metrics from CSV
- `analysis/plot_results.py`: Plot offset and delay trends
- `utils/packet_format.py`: JSON packet builders/validators
- `utils/statistics_tools.py`: Drift and summary statistics
- `results/sync_data.csv`: Synchronization output samples

## Setup

1. Install dependencies:

```powershell
pip install -r requirements.txt
```

2. Generate TLS certificate/key if needed:

```powershell
python generate_cert.py --ips 127.0.0.1 --dns localhost
```

## Run

### 1. Start secure server (recommended)

```powershell
python server/secure_server.py --host 0.0.0.0 --port 6000 --ntp-server pool.ntp.org
```

### 2. Run secure client

```powershell
python client/client.py --host 127.0.0.1 --port 6000 --server-hostname localhost --rounds 10 --drift 0.5
```

Data is appended to `results/sync_data.csv`.

### Optional: UDP server

```powershell
python server/server.py --host 0.0.0.0 --port 5005
```

## Analysis

### Drift estimate

```powershell
python analysis/drift_estimator.py --input results/sync_data.csv
```

### Accuracy summary

```powershell
python analysis/accuracy_evaluator.py --input results/sync_data.csv
```

### Plot trends

```powershell
python analysis/plot_results.py --input results/sync_data.csv
```

Or save figure:

```powershell
python analysis/plot_results.py --input results/sync_data.csv --output results/sync_plot.png
```

## GUI

Run the integrated Tkinter control center:

```powershell
python gui_app.py
```

From the GUI, you can:
- Start and stop UDP and TLS servers.
- Run secure client synchronization with custom rounds/drift/output path.
- Execute drift and accuracy analysis scripts.
- Load CSV results into a table and view embedded delay/offset plots.
- Monitor all processes using live logs.
