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

### 1. Raw Socket Programming - Server Socket Lifecycle

Demonstrates explicit socket operations: create, bind, listen, and accept.

```python
import socket
import ssl
import threading
import logging

class RawSocketServer:
    """Low-level socket programming without high-level frameworks"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 6000, backlog: int = 5):
        self.host = host
        self.port = port
        self.backlog = backlog
        self.logger = logging.getLogger(__name__)
        
        # STEP 1: CREATE socket
        self.server_socket = socket.socket(
            socket.AF_INET,          # IPv4 address family
            socket.SOCK_STREAM       # TCP stream socket
        )
        
        # Configure socket options
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self.server_socket.settimeout(30.0)  # 30 second timeout
        
        self.running = False
        self.active_connections = 0
        self.connection_lock = threading.Lock()
    
    def start(self):
        """Bind socket to address and start listening"""
        try:
            # STEP 2: BIND socket to address and port
            self.server_socket.bind((self.host, self.port))
            self.logger.info(f"Socket bound to {self.host}:{self.port}")
            
            # STEP 3: LISTEN for incoming connections
            self.server_socket.listen(self.backlog)
            self.logger.info(f"Server listening with backlog={self.backlog}")
            
            self.running = True
            self._accept_connections()
        
        except OSError as e:
            self.logger.error(f"Socket bind/listen failed: {e}")
            self.server_socket.close()
            raise
    
    def _accept_connections(self):
        """STEP 4: ACCEPT incoming connections"""
        while self.running:
            try:
                # Accept connection (blocks until client connects)
                client_socket, client_address = self.server_socket.accept()
                self.logger.info(f"Connection accepted from {client_address}")
                
                with self.connection_lock:
                    self.active_connections += 1
                
                # Handle client in separate thread
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.timeout:
                continue
            except OSError as e:
                if self.running:
                    self.logger.error(f"Accept failed: {e}")
    
    def _handle_client(self, client_socket: socket.socket, client_address: tuple):
        """Handle individual client connection"""
        try:
            # STEP 5: SEND/RECEIVE data
            client_socket.settimeout(5.0)
            
            # Receive data from client
            data = client_socket.recv(1024)
            if data:
                self.logger.info(f"Received from {client_address}: {data.decode()}")
                
                # Send response back to client
                response = f"Server received: {data.decode()}".encode()
                bytes_sent = client_socket.sendall(response)
                self.logger.info(f"Sent {len(response)} bytes to {client_address}")
        
        except socket.timeout:
            self.logger.warning(f"Timeout on connection from {client_address}")
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
        finally:
            # Properly close socket
            client_socket.close()
            with self.connection_lock:
                self.active_connections -= 1
            self.logger.info(f"Connection closed: {client_address}")
    
    def stop(self):
        """Gracefully shutdown server"""
        self.running = False
        self.server_socket.close()
        self.logger.info("Server shutdown complete")
```

### 2. Client Socket Programming - Connect and Communication

```python
import socket
import ssl
import time

class RawSocketClient:
    """Low-level client socket operations"""
    
    def __init__(self, host: str, port: int, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.client_socket = None
    
    def connect(self) -> bool:
        """CREATE socket and CONNECT to server"""
        try:
            # CREATE a new socket
            self.client_socket = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )
            self.client_socket.settimeout(self.timeout)
            
            # CONNECT to server
            print(f"Connecting to {self.host}:{self.port}...")
            self.client_socket.connect((self.host, self.port))
            print(f"Connected successfully")
            return True
        
        except ConnectionRefusedError:
            print(f"Error: Connection refused by {self.host}:{self.port}")
            return False
        except socket.timeout:
            print(f"Error: Connection timeout after {self.timeout}s")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def send_data(self, data: str) -> bool:
        """SEND data to server"""
        try:
            encoded_data = data.encode()
            self.client_socket.sendall(encoded_data)
            print(f"Sent: {data}")
            return True
        except Exception as e:
            print(f"Send error: {e}")
            return False
    
    def receive_data(self, buffer_size: int = 1024) -> str:
        """RECEIVE data from server"""
        try:
            data = self.client_socket.recv(buffer_size)
            if data:
                return data.decode()
            else:
                print("Connection closed by server")
                return None
        except Exception as e:
            print(f"Receive error: {e}")
            return None
    
    def close(self):
        """Close socket connection"""
        if self.client_socket:
            self.client_socket.close()
            print("Connection closed")
```

### 3. SSL/TLS Secure Communication - Server Side

```python
import ssl
import socket
import threading
import logging
from pathlib import Path

class SecureServer:
    """Demonstrates SSL/TLS encrypted socket communication"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 6000,
                 cert_file: str = "certs/server.crt", 
                 key_file: str = "certs/server.key"):
        self.host = host
        self.port = port
        self.cert_file = cert_file
        self.key_file = key_file
        self.logger = logging.getLogger(__name__)
        
        # Initialize SSL context with TLS protocol
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        # Configure TLS version and ciphers
        self.ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.ssl_context.options |= ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        
        try:
            # Load certificate and private key
            self.ssl_context.load_cert_chain(cert_file, key_file)
            self.logger.info(f"Loaded certificate: {cert_file}")
        except FileNotFoundError as e:
            self.logger.error(f"Certificate/Key file not found: {e}")
            raise
        except ssl.SSLError as e:
            self.logger.error(f"SSL error loading certificates: {e}")
            raise
        
        # Create and configure server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = False
    
    def start(self):
        """Start secure server"""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            self.logger.info(f"Secure server listening on {self.host}:{self.port}")
            self._accept_secure_connections()
        except Exception as e:
            self.logger.error(f"Server start failed: {e}")
            raise
    
    def _accept_secure_connections(self):
        """Accept and wrap connections with SSL"""
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                self.logger.info(f"Client connection from {addr}")
                
                # Handle SSL handshake in separate thread
                thread = threading.Thread(
                    target=self._handle_ssl_client,
                    args=(client_socket, addr)
                )
                thread.daemon = True
                thread.start()
                
            except KeyboardInterrupt:
                self.running = False
                break
            except Exception as e:
                self.logger.error(f"Accept error: {e}")
    
    def _handle_ssl_client(self, client_socket: socket.socket, addr: tuple):
        """Handle SSL/TLS handshake and communication"""
        try:
            # Wrap socket with SSL/TLS
            ssl_socket = self.ssl_context.wrap_socket(
                client_socket,
                server_side=True
            )
            
            # Perform SSL handshake
            ssl_socket.do_handshake()
            self.logger.info(f"SSL handshake successful with {addr}")
            self.logger.info(f"TLS version: {ssl_socket.version()}")
            self.logger.info(f"Cipher: {ssl_socket.cipher()}")
            
            # Receive encrypted data
            data = ssl_socket.recv(1024)
            if data:
                self.logger.info(f"Encrypted data from {addr}: {data.decode()}")
            
            # Send encrypted response
            response = "Secure data received".encode()
            ssl_socket.sendall(response)
            
        except ssl.SSLError as e:
            self.logger.error(f"SSL error with {addr}: {e}")
        except Exception as e:
            self.logger.error(f"Error handling client {addr}: {e}")
        finally:
            ssl_socket.close()
            self.logger.info(f"SSL connection closed: {addr}")
```

### 4. Multi-Client Concurrent Handling with Thread Pool

```python
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

class ConcurrentServer:
    """Handle multiple concurrent clients with thread pool"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 6000, 
                 max_workers: int = 10):
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # Thread-safe metrics
        self.metrics_lock = Lock()
        self.total_clients = 0
        self.active_clients = 0
        self.total_requests = 0
        self.request_times = []
    
    def handle_client(self, client_socket: socket.socket, addr: tuple, client_id: int):
        """Handle individual client with performance tracking"""
        start_time = time.time()
        
        try:
            client_socket.settimeout(30)
            
            # Receive request
            request_start = time.time()
            data = client_socket.recv(4096)
            request_duration = time.time() - request_start
            
            if data:
                message = data.decode()
                print(f"[Client {client_id}] Received: {message}")
                
                # Process request
                processing_start = time.time()
                time.sleep(0.1)  # Simulate processing
                processing_duration = time.time() - processing_start
                
                # Send response
                response = f"ACK: {message}".encode()
                send_start = time.time()
                client_socket.sendall(response)
                send_duration = time.time() - send_start
                
                # Update metrics
                total_duration = time.time() - start_time
                with self.metrics_lock:
                    self.total_requests += 1
                    self.request_times.append({
                        'client_id': client_id,
                        'receive_time': request_duration,
                        'process_time': processing_duration,
                        'send_time': send_duration,
                        'total_time': total_duration
                    })
                
                print(f"[Client {client_id}] Response time: {total_duration:.4f}s")
        
        except socket.timeout:
            print(f"[Client {client_id}] Request timeout")
        except Exception as e:
            print(f"[Client {client_id}] Error: {e}")
        finally:
            client_socket.close()
            with self.metrics_lock:
                self.active_clients -= 1
    
    def start_server(self):
        """Start server accepting multiple concurrent clients"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(self.max_workers)
        
        print(f"Server listening on {self.host}:{self.port}")
        print(f"Max concurrent clients: {self.max_workers}")
        
        try:
            client_counter = 0
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                    client_counter += 1
                    
                    with self.metrics_lock:
                        self.total_clients += 1
                        self.active_clients += 1
                    
                    print(f"[{client_counter}] Connection from {addr}")
                    
                    # Submit to thread pool
                    self.executor.submit(
                        self.handle_client,
                        client_socket,
                        addr,
                        client_counter
                    )
                
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Accept error: {e}")
        
        finally:
            server_socket.close()
            self.executor.shutdown(wait=True)
            self.print_metrics()
    
    def print_metrics(self):
        """Print performance metrics"""
        print("\n=== Performance Metrics ===")
        print(f"Total clients: {self.total_clients}")
        print(f"Total requests: {self.total_requests}")
        
        if self.request_times:
            avg_time = sum(r['total_time'] for r in self.request_times) / len(self.request_times)
            max_time = max(r['total_time'] for r in self.request_times)
            min_time = min(r['total_time'] for r in self.request_times)
            
            print(f"Average response time: {avg_time:.4f}s")
            print(f"Max response time: {max_time:.4f}s")
            print(f"Min response time: {min_time:.4f}s")
            print(f"Throughput: {self.total_requests/sum(r['total_time'] for r in self.request_times):.2f} req/s")
```

### 5. Error Handling and Edge Cases

```python
import socket
import ssl
import logging
from typing import Optional

class RobustClient:
    """Client with comprehensive error handling and edge case management"""
    
    def __init__(self, host: str, port: int, max_retries: int = 3):
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.socket = None
        self.logger = logging.getLogger(__name__)
    
    def connect_with_retry(self) -> bool:
        """Connect with exponential backoff retry strategy"""
        for attempt in range(self.max_retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10)
                self.socket.connect((self.host, self.port))
                self.logger.info(f"Connected successfully on attempt {attempt + 1}")
                return True
            
            except ConnectionRefusedError:
                self.logger.warning(f"Connection refused, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            except socket.timeout:
                self.logger.warning(f"Connection timeout, attempt {attempt + 1}/{self.max_retries}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
            
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                return False
            
            finally:
                if attempt < self.max_retries - 1 and self.socket:
                    self.socket.close()
        
        return False
    
    def send_with_validation(self, data: bytes) -> bool:
        """Send data with validation and error handling"""
        if not self.socket:
            self.logger.error("Socket not connected")
            return False
        
        try:
            if len(data) == 0:
                self.logger.error("Cannot send empty data")
                return False
            
            if len(data) > 1048576:  # 1MB limit
                self.logger.error("Data exceeds maximum size")
                return False
            
            self.socket.sendall(data)
            self.logger.info(f"Sent {len(data)} bytes")
            return True
        
        except BrokenPipeError:
            self.logger.error("Connection broken (BrokenPipeError)")
            self.disconnect()
            return False
        
        except socket.timeout:
            self.logger.error("Send timeout")
            return False
        
        except Exception as e:
            self.logger.error(f"Send failed: {e}")
            return False
    
    def receive_with_timeout(self, buffer_size: int = 4096) -> Optional[bytes]:
        """Receive data with timeout and partial failure handling"""
        if not self.socket:
            self.logger.error("Socket not connected")
            return None
        
        try:
            data = self.socket.recv(buffer_size)
            if not data:
                self.logger.warning("Server closed connection")
                return None
            
            self.logger.info(f"Received {len(data)} bytes")
            return data
        
        except socket.timeout:
            self.logger.error("Receive timeout")
            return None
        
        except ConnectionResetError:
            self.logger.error("Connection reset by peer")
            self.disconnect()
            return None
        
        except Exception as e:
            self.logger.error(f"Receive failed: {e}")
            return None
    
    def ssl_handshake_with_verification(self, hostname: str) -> bool:
        """Perform SSL handshake with certificate verification"""
        try:
            context = ssl.create_default_context()
            context.check_hostname = True
            context.verify_mode = ssl.CERT_REQUIRED
            
            ssl_socket = context.wrap_socket(self.socket, server_hostname=hostname)
            self.socket = ssl_socket
            
            # Verify certificate
            cert = ssl_socket.getpeercert()
            self.logger.info(f"Certificate verified: {cert['subject']}")
            return True
        
        except ssl.SSLError as e:
            self.logger.error(f"SSL verification failed: {e}")
            return False
        
        except ssl.CertificateError as e:
            self.logger.error(f"Certificate error: {e}")
            return False
        
        except Exception as e:
            self.logger.error(f"SSL handshake failed: {e}")
            return False
    
    def disconnect(self):
        """Gracefully disconnect"""
        if self.socket:
            try:
                self.socket.close()
                self.logger.info("Disconnected")
            except Exception as e:
                self.logger.error(f"Error closing socket: {e}")
            finally:
                self.socket = None
```

### 6. Performance Measurement and Metrics

```python
import time
import statistics
from dataclasses import dataclass
from typing import List

@dataclass
class PerformanceMetrics:
    """Store performance measurements"""
    response_times: List[float]
    throughput: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    error_rate: float

class PerformanceMonitor:
    """Monitor and measure performance metrics"""
    
    def __init__(self):
        self.request_times = []
        self.error_count = 0
        self.success_count = 0
        self.start_time = time.time()
    
    def record_request(self, duration: float, success: bool = True):
        """Record request performance"""
        self.request_times.append(duration)
        if success:
            self.success_count += 1
        else:
            self.error_count += 1
    
    def get_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics"""
        if not self.request_times:
            return None
        
        sorted_times = sorted(self.request_times)
        elapsed = time.time() - self.start_time
        
        return PerformanceMetrics(
            response_times=self.request_times,
            throughput=self.success_count / elapsed,
            latency_p50=statistics.median(sorted_times),
            latency_p95=sorted_times[int(len(sorted_times) * 0.95)],
            latency_p99=sorted_times[int(len(sorted_times) * 0.99)],
            error_rate=self.error_count / (self.success_count + self.error_count)
        )
    
    def print_report(self):
        """Print performance report"""
        metrics = self.get_metrics()
        if metrics:
            print("\n=== Performance Report ===")
            print(f"Total Requests: {self.success_count + self.error_count}")
            print(f"Successful: {self.success_count}")
            print(f"Failed: {self.error_count}")
            print(f"Error Rate: {metrics.error_rate*100:.2f}%")
            print(f"Throughput: {metrics.throughput:.2f} req/s")
            print(f"Latency (P50): {metrics.latency_p50*1000:.2f}ms")
            print(f"Latency (P95): {metrics.latency_p95*1000:.2f}ms")
            print(f"Latency (P99): {metrics.latency_p99*1000:.2f}ms")
```

### 7. Stress Testing with Multiple Concurrent Clients

```python
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class StressTest:
    """Stress test server with multiple concurrent clients"""
    
    def __init__(self, host: str, port: int, num_clients: int = 10,
                 requests_per_client: int = 100):
        self.host = host
        self.port = port
        self.num_clients = num_clients
        self.requests_per_client = requests_per_client
        self.monitor = PerformanceMonitor()
    
    def client_worker(self, client_id: int) -> dict:
        """Simulate individual client"""
        client = RobustClient(self.host, self.port, max_retries=3)
        
        if not client.connect_with_retry():
            print(f"[Client {client_id}] Failed to connect")
            return {'client_id': client_id, 'success': False}
        
        for req_id in range(self.requests_per_client):
            request_time = time.time()
            
            # Send request
            success = client.send_with_validation(
                f"Request {req_id} from client {client_id}".encode()
            )
            
            if success:
                response = client.receive_with_timeout()
                duration = time.time() - request_time
                self.monitor.record_request(duration, response is not None)
            else:
                self.monitor.record_request(0, False)
        
        client.disconnect()
        return {'client_id': client_id, 'success': True}
    
    def run_stress_test(self):
        """Execute stress test"""
        print(f"Starting stress test: {self.num_clients} clients, "
              f"{self.requests_per_client} requests each")
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=min(self.num_clients, 50)) as executor:
            futures = [
                executor.submit(self.client_worker, i)
                for i in range(self.num_clients)
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                except Exception as e:
                    print(f"Client error: {e}")
        
        elapsed = time.time() - start_time
        print(f"\nStress test completed in {elapsed:.2f}s")
        self.monitor.print_report()
```

### 8. MasterClock Implementation

```python
class MasterClock:
    def __init__(self, ntp_server: str = PRIMARY_NTP_SERVER, sync_interval: int = 30):
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

    def now(self) -> float:
        with self._lock:
            offset = self._offset
        return time.time() + offset

    def status(self) -> str:
        with self._lock:
            return self._last_sync_status

    def _sync_loop(self) -> None:
        while not self._stop_event.is_set():
            reference_time, source = fetch_reference_time(self.ntp_server)
            with self._lock:
                if reference_time is None:
                    self._last_sync_status = source
                else:
                    self._offset = compute_reference_offset(reference_time)
                    self._last_sync_status = source
            self._stop_event.wait(self.sync_interval)
```

### 9. Client Synchronization Request

```python
def sync_with_server(server_socket, client_id: str) -> dict:
    client_time = time.time()
    
    request = {
        "type": "SYNC_REQUEST",
        "client_id": client_id,
        "client_time": client_time,
        "round": sync_round
    }
    
    try:
        send_json(server_socket, request)
        response = recv_json(server_socket)
        
        return {
            "server_time": response["server_time"],
            "offset": response["offset"],
            "ntp_status": response["ntp_status"],
            "latency": time.time() - client_time
        }
    except Exception as e:
        logging.error(f"Sync request failed: {e}")
        return None
```

### 10. Generic JSON Message Protocol

```python
import json
import struct

def send_json(sock, data):
    """Send JSON with 4-byte length prefix"""
    message = json.dumps(data).encode('utf-8')
    length = struct.pack("!I", len(message))
    sock.sendall(length + message)

def recv_json(sock):
    """Receive JSON with 4-byte length prefix"""
    raw_length = sock.recv(4)
    if not raw_length:
        return None
    
    length = struct.unpack("!I", raw_length)[0]
    if length > 10485760:  # 10MB max
        raise ValueError("Message too large")
    
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
