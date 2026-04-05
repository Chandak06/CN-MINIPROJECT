# Distributed Network Time Protocol (NTP) Synchronization System

A comprehensive distributed clock synchronization system using low-level socket programming with SSL/TLS encryption. This project implements a multi-client concurrent architecture that synchronizes system clocks across networked machines with high accuracy using NTP as a reference time source and demonstrates synchronization performance under various load conditions.

## Table of Contents
- [Features](#features)
- [Project Structure](#project-structure)
- [System Requirements](#system-requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [How It Works](#how-it-works)
- [Synchronization Algorithm](#synchronization-algorithm)
- [Performance Analysis](#performance-analysis)
- [Code Snippets](#code-snippets)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

## Features

✨ **Core Features:**
- 🔐 **Secure Communication** - SSL/TLS encryption for all client-server communication
- 🌐 **Multi-Client Support** - Concurrent socket handling for multiple simultaneous clients
- ⏱️ **NTP Integration** - Synchronization with public NTP servers (pool.ntp.org)
- 🔄 **Automatic Clock Adjustment** - Dynamic time adjustment using NTP reference values
- 📊 **Real-Time GUI Monitoring** - Dark-themed Tkinter interface for both server and client
- 📈 **Drift Estimation** - Measure and analyze clock drift over time
- 📉 **Accuracy Evaluation** - Comprehensive accuracy metrics and statistics
- 🎨 **Performance Analysis** - Graphical visualization of synchronization results
- 📝 **CSV Data Logging** - Persistent storage of synchronization metrics
- 🔌 **Configurable Parameters** - Customizable IPs, ports, intervals, and drift settings

## Project Structure

```
├── certs/                          # SSL/TLS certificates directory
│   ├── server.crt                  # Server certificate
│   └── server.key                  # Server private key
├── client/                         # Client-side modules
│   ├── client.py                   # Core client implementation
│   ├── client_gui.py               # Client GUI interface
│   ├── sync_algorithm.py           # Synchronization algorithm logic
│   ├── time_adjuster.py            # Time adjustment mechanism
│   └── ntp_sync.py                 # NTP communication layer
├── server/                         # Server-side modules
│   ├── server.py                   # Core server implementation
│   ├── server_gui.py               # Server GUI interface
│   ├── secure_server.py            # Secure socket wrapper
│   ├── time_manager.py             # Master clock management
│   ├── ntp_sync.py                 # NTP synchronization
│   ├── test.py                     # Server testing utilities
│   └── config.cnf                  # Server configuration
├── analysis/                       # Data analysis modules
│   ├── accuracy_evaluator.py       # Accuracy metrics calculation
│   ├── drift_estimator.py          # Clock drift analysis
│   └── plot_results.py             # Visualization of results
├── results/                        # Output data directory
│   ├── sync_data.csv               # Synchronization records
│   ├── client_sync_data.csv        # Client-specific sync data
│   ├── stress_sync_data.csv        # Stress test results
│   └── accuracy_output.txt         # Accuracy evaluation report
├── utils/                          # Utility modules
│   ├── packet_format.py            # Network packet structure
│   ├── statistics_tools.py         # Statistical analysis tools
│   └── config.cnf                  # Configuration file
├── generate_cert.py                # SSL certificate generation utility
├── requirements.txt                # Python dependencies
└── README.md                       # Project documentation
```

## System Requirements

### Minimum Requirements
- **Operating System:** Windows 10/11, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Python Version:** Python 3.8 or higher
- **RAM:** 512 MB minimum, 1 GB recommended
- **Storage:** 100 MB free space
- **Network:** Active internet connection for NTP server access

### Python Dependencies
```
cryptography>=42.0.0          # SSL/TLS certificate handling
matplotlib>=3.8.0             # Graphical data visualization
ntplib>=0.4.0                 # NTP protocol implementation
tkinter                       # GUI framework (bundled with Python)
```

Standard library modules (pre-installed):
- `socket` - Network socket programming
- `ssl` - SSL/TLS encryption support
- `threading` - Multi-threaded operations
- `struct` - Binary data handling
- `csv` - Data persistence
- `json` - Configuration management
- `time` - Time operations
- `datetime` - Date/time utilities
- `os` - Operating system interface
- `sys` - System-specific parameters
- `argparse` - Command-line argument parsing

### Hardware Requirements
- **Processor:** 1 GHz or faster processor
- **Display:** 1024x768 resolution or higher (for GUI)
- **Network Interface:** Ethernet or Wi-Fi adapter
- **Ports:** TCP port 6000 or custom configured port

### Network Requirements
- Network connectivity to NTP servers (pool.ntp.org)
- Firewall configured to allow synchronization port
- For multi-machine setup: Network accessibility between server and clients

**Note:** NTP servers must be accessible from the system running the server.

## Installation

### Step 1: Clone/Download the Project
```bash
cd CN-MINIPROJECT
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

On Linux, also install tkinter:
```bash
sudo apt install python3-tk
```

### Step 3: Generate SSL/TLS Certificates
Generate certificates for your specific IP addresses and hostname:

For localhost testing:
```bash
python generate_cert.py --ips 127.0.0.1 --dns localhost --common-name localhost
```

For specific network:
```bash
python generate_cert.py --ips 127.0.0.1 192.168.29.168 --dns localhost --common-name 192.168.29.168
```

This creates:
- `certs/server.crt` - Server certificate
- `certs/server.key` - Server private key

### Step 4: Verify Installation
```bash
python -c "import socket, ssl, ntplib, cryptography; print('All dependencies installed successfully')"
```

## Usage

### Starting the Server

Run the server GUI application:
```bash
python server/server_gui.py [--port PORT] [--sync-interval INTERVAL] [--ntp-server SERVER]
```

**Parameters:**
- `--port` - Listen port (default: 6000)
- `--sync-interval` - NTP sync interval in seconds (default: 30)
- `--ntp-server` - NTP server address (default: pool.ntp.org)

**Server Interface:**
- Displays active client connections
- Shows master clock status
- Displays real-time synchronization metrics
- Logs all client activities
- Shows NTP synchronization status

### Connecting Clients

In a separate terminal/machine, run:
```bash
python client/client_gui.py --host SERVER_IP --port PORT [--server-hostname HOSTNAME] [--rounds ROUNDS] [--drift DRIFT]
```

**Parameters:**
- `--host` - Server IP address (required)
- `--port` - Server port (default: 6000)
- `--server-hostname` - Server hostname for SSL verification (default: localhost)
- `--rounds` - Number of synchronization rounds (default: 10)
- `--drift` - Simulated clock drift in PPM (parts per million)

**Client Features:**
- Connect to server with SSL/TLS
- Request time synchronization
- Display local vs. synchronized time
- Track synchronization metrics
- View accuracy statistics
- Clear results and start new session

### Example Commands

**Server (localhost testing):**
```bash
python server/server_gui.py --port 6000 --sync-interval 30
```

**Single Client:**
```bash
python client/client_gui.py --host 127.0.0.1 --port 6000 --server-hostname localhost --rounds 10 --drift 0.5
```

**Multiple Clients (simulate stress test):**
Terminal 1:
```bash
python server/server_gui.py --port 6000
```

Terminal 2:
```bash
python client/client_gui.py --host 127.0.0.1 --port 6000 --rounds 20
```

Terminal 3:
```bash
python client/client_gui.py --host 127.0.0.1 --port 6000 --rounds 20
```

### Data Analysis

After running synchronization tests, analyze results:

```bash
# View drift estimation
python analysis/drift_estimator.py

# Evaluate accuracy
python analysis/accuracy_evaluator.py

# Plot visualization
python analysis/plot_results.py
```

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────┐
│                   NTP NETWORK                       │
│              (pool.ntp.org reference)               │
└────────────────────────┬────────────────────────────┘
                         │
                         │ NTP queries
                         ↓
┌─────────────────────────────────────────────────────┐
│              SERVER INFRASTRUCTURE                  │
│  ┌──────────────────────────────────┐               │
│  │  NTP Sync Module                 │               │
│  │  (ntp_sync.py)                   │               │
│  │  • Fetch reference time           │               │
│  │  • Calculate offset               │               │
│  │  • Error handling                 │               │
│  └──────────────────────────────────┘               │
│           ↓                                         │
│  ┌──────────────────────────────────┐               │
│  │  Master Clock              │
│  │  (time_manager.py)               │               │
│  │  • Maintains system offset        │               │
│  │  • Periodic NTP sync              │               │
│  │  • Thread-safe clock operations   │               │
│  └──────────────────────────────────┘               │
│           ↓                                         │
│  ┌──────────────────────────────────┐               │
│  │  Secure Server Engine            │               │
│  │  (server.py/server_gui.py)       │               │
│  │  • SSL/TLS listener (port 6000)   │               │
│  │  • Multi-threaded connection      │               │
│  │    handling                       │               │
│  │  • Time distribution protocol     │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
          ↕ Secure TLS over TCP ↕
┌─────────────────────────────────────────────────────┐
│           CLIENT CONNECTION LAYER                   │
│  ┌──────────────────────────────────┐               │
│  │  Client 1 (localhost)            │               │
│  │  ├─ TLS Connection               │               │
│  │  ├─ Sync Algorithm               │               │
│  │  ├─ Time Adjuster                │               │
│  │  └─ Local Clock Monitor          │               │
│  └──────────────────────────────────┘               │
│                                                     │
│  ┌──────────────────────────────────┐               │
│  │  Client 2 (Network machine)      │               │
│  │  ├─ TLS Connection               │               │
│  │  ├─ Sync Algorithm               │               │
│  │  ├─ Time Adjuster                │               │
│  │  └─ Local Clock Monitor          │               │
│  └──────────────────────────────────┘               │
│                                                     │
│  ┌──────────────────────────────────┐               │
│  │  Client N (Multiple instances)   │               │
│  │  [Similar structure repeated]    │               │
│  └──────────────────────────────────┘               │
└─────────────────────────────────────────────────────┘
          ↓ Results & Metrics ↓
┌─────────────────────────────────────────────────────┐
│           ANALYSIS & EVALUATION LAYER               │
│  ├─ Drift Estimator                                │
│  ├─ Accuracy Evaluator                             │
│  ├─ Plot & Visualization                           │
│  └─ CSV Data Storage                               │
└─────────────────────────────────────────────────────┘
```

### Communication Protocol

**Message Structure:**
- All messages use TLS encryption over TCP
- JSON format for data exchange
- 4-byte length prefix for message boundaries

**Message Types:**

1. **SYNC_REQUEST** - Client requests time synchronization
   ```json
   {
     "type": "SYNC_REQUEST",
     "client_id": "client_1",
     "client_time": 1234567890.123
   }
   ```

2. **SYNC_RESPONSE** - Server provides synchronized time
   ```json
   {
     "type": "SYNC_RESPONSE",
     "server_time": 1234567900.456,
     "offset": 10.333,
     "ntp_status": "synchronized"
   }
   ```

3. **HEARTBEAT** - Periodic connection check
   ```json
   {
     "type": "HEARTBEAT",
     "server_clock": 1234567910.789
   }
   ```

## How It Works

### Synchronization Flow

1. **Server Initialization**
   - Server starts and initializes MasterClock
   - Begins periodic NTP synchronization (default: every 30 seconds)
   - Listens for incoming TLS connections on port 6000

2. **Client Connection**
   - Client establishes secure TLS connection to server
   - Server accepts and logs connection
   - Client enters synchronization loop

3. **Time Synchronization** (per round)
   - Client reads local system time (potentially with simulated drift)
   - Client sends SYNC_REQUEST with current time to server
   - Server responds with synchronized server time and calculated offset
   - Client applies time adjustment using received offset
   - Metrics recorded: round-trip delay, offset, accuracy

4. **Continuous Adjustment**
   - Client continues requesting time sync at intervals
   - Time adjustments are applied smoothly to local clock
   - Drift is continuously corrected

5. **Data Collection & Analysis**
   - All synchronization events logged to CSV files
   - Metrics include: request time, response time, calculated offset, accuracy deviation
   - After test completion: accuracy and drift analysis performed

## Synchronization Algorithm

### Algorithm Overview

The system implements a client-server synchronization algorithm based on NTP principles:

```
Client                           Server
  |                              |
  | <--- SYNC_REQUEST ---|       |
  |    (client_time)      |      |
  |                       |----> | Calculate offset
  |                       | NTP  | (reference_time - client_time)
  | <--- SYNC_RESPONSE --|      |
  |   (server_time, offset)     |
  |                            |
  | Apply offset              |
  | adjusted_time =           |
  |   local_time + offset     |
  |                           |
```

### Key Components

**MasterClock (server/time_manager.py):**
- Synchronizes with NTP server at regular intervals
- Maintains calculated offset from system time
- Thread-safe clock queries
- Graceful fallback if NTP unavailable

**SyncAlgorithm (client/sync_algorithm.py):**
- Implements client-side synchronization logic
- Applies exponential smoothing to avoid abrupt adjustments
- Tracks synchronization accuracy over multiple rounds

**TimeAdjuster (client/time_adjuster.py):**
- Simulates clock drift for testing
- Applies adjustments based on server feedback
- Maintains adjustment history

### Accuracy Metrics

- **Clock Offset:** Difference between client's local time and server's synchronized time
- **Synchronization Error:** Deviation after applying server's recommended offset
- **Drift Rate:** Rate of clock drift expressed in PPM (parts per million)
- **Convergence Time:** Time required for client clock to converge with server

## Performance Analysis

### Drift Estimation (`analysis/drift_estimator.py`)

Analyzes clock drift patterns:
- Calculates drift rate from collected samples
- Identifies drift trends over time
- Compares simulated vs. actual drift
- Generates drift report

### Accuracy Evaluation (`analysis/accuracy_evaluator.py`)

Measures synchronization quality:
- Calculates mean absolute error (MAE)
- Computes standard deviation of errors
- Generates accuracy statistics
- Creates performance summary

### Visualization (`analysis/plot_results.py`)

Generates graphical representations:
- Time offset over sync rounds
- Accuracy error distribution
- Drift trending
- Multi-client comparison plots

## Code Snippets

### 1. MasterClock Implementation

```python
class MasterClock:
    def __init__(self, ntp_server: str = PRIMARY_NTP_SERVER, sync_interval: int = 30):
        self.ntp_server = ntp_server
        self.sync_interval = sync_interval
        self._offset = 0.0
        self._last_sync_status = "system-time"
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()

    def now(self):
        with self._lock:
            offset = self._offset
        return time.time() + offset

    def _sync_loop(self):
        while not self._stop_event.is_set():
            reference_time, source = fetch_reference_time(self.ntp_server)
            with self._lock:
                if reference_time is not None:
                    self._offset = compute_reference_offset(reference_time)
                    self._last_sync_status = source
            self._stop_event.wait(self.sync_interval)
```

### 2. Secure Server Socket Setup

```python
class SecureServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 6000):
        self.host = host
        self.port = port
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain("certs/server.crt", "certs/server.key")
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ssl_context = context
        
    def accept_connection(self):
        self.socket.bind((self.host, self.port))
        self.socket.listen(5)
        client_socket, addr = self.socket.accept()
        ssl_socket = self.ssl_context.wrap_socket(client_socket, server_side=True)
        return ssl_socket, addr
```

### 3. Client Synchronization Request

```python
def sync_with_server(server_socket, client_id: str) -> dict:
    client_time = time.time()
    
    request = {
        "type": "SYNC_REQUEST",
        "client_id": client_id,
        "client_time": client_time
    }
    
    # Send request
    send_json(server_socket, request)
    
    # Receive response
    response = recv_json(server_socket)
    
    return {
        "server_time": response["server_time"],
        "offset": response["offset"],
        "ntp_status": response["ntp_status"]
    }
```

### 4. Generic JSON Message Protocol

```python
import json
import struct

def send_json(sock, data):
    message = json.dumps(data).encode('utf-8')
    length = struct.pack("!I", len(message))
    sock.sendall(length + message)

def recv_json(sock):
    raw_length = sock.recv(4)
    if not raw_length:
        return None
    length = struct.unpack("!I", raw_length)[0]
    data = b""
    while len(data) < length:
        chunk = sock.recv(min(4096, length - len(data)))
        if not chunk:
            return None
        data += chunk
    return json.loads(data.decode('utf-8'))
```

## Configuration

### config.cnf File

```ini
[server]
host = 0.0.0.0
port = 6000
sync_interval = 30
ntp_server = pool.ntp.org

[ssl]
cert_file = certs/server.crt
key_file = certs/server.key
min_version = TLSv1.2

[client]
rounds = 10
drift = 0.5
timeout = 5

[logging]
enable_csv = true
results_dir = results/
```

### Certificate Generation

Generate certificates with specific parameters:

```bash
# For localhost
python generate_cert.py --ips 127.0.0.1 --dns localhost --common-name localhost

# For multiple IPs
python generate_cert.py --ips 127.0.0.1 192.168.1.100 --dns server.local --common-name server.local

# Custom validity period
python generate_cert.py --ips 127.0.0.1 --valid-days 365
```

## Troubleshooting

### Common Issues

**Issue: "Certificate verification failed"**
- Solution: Regenerate certificates with correct IP/hostname
- Ensure `--server-hostname` matches certificate's common name

**Issue: "Address already in use"**
- Solution: Port 6000 is already in use
- Use different port: `python server/server_gui.py --port 6001`
- Or kill existing process using the port

**Issue: "NTP server not accessible"**
- Solution: Check internet connection and firewall settings
- Falls back to system time if NTP unavailable
- Server continues functioning with degraded synchronization

**Issue: "Connection refused"**
- Solution: Ensure server is running on correct IP/port
- Check firewall allows connections on specified port
- Verify server hostname matches client connection string

**Issue: "Tkinter not found on Linux"**
- Solution: Install tkinter package
```bash
sudo apt install python3-tk
```

**Issue: "High synchronization error despite correct IP"**
- Solution: Check network latency between client and server
- Consider running on same machine for testing
- Increase `--rounds` parameter for averaging effects

### Debugging

Enable verbose logging:
```bash
# Server with debug output
python server/server_gui.py --debug

# Client with debug output  
python client/client_gui.py --host 127.0.0.1 --debug
```

View detailed logs:
```bash
python analysis/accuracy_evaluator.py --verbose
python analysis/drift_estimator.py --verbose
```

## Performance Benchmarks

Typical synchronization accuracy (on local network):
- **Mean Accuracy:** < 100 ms
- **Std Deviation:** < 50 ms
- **Convergence Time:** 3-5 synchronization rounds
- **Drift Correction:** < 0.1% after adjustment

Results vary based on:
- Network latency and jitter
- System load
- Number of concurrent clients
- Simulated drift parameters

## References

- RFC 5905: Network Time Protocol Version 4
- ntplib Documentation
- Python ssl module documentation
- Socket programming best practices

## License

This project is part of Computer Networks Mini Project curriculum.

## Author

Created for Computer Networks Mini Project (Semester 4)

---

*For questions or issues, refer to the project documentation or contact the development team.*
