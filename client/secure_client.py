import json
import os
import argparse
import socket
import ssl
import statistics
import threading
import time

DEFAULT_HOST = os.getenv("CLOCKSYNC_SERVER_IP", "127.0.0.1")
DEFAULT_PORT = 6000
BUFFER_SIZE = 1024
NUM_SYNCS = 10
REQUEST_INTERVAL_SECONDS = 1
SOCKET_TIMEOUT_SECONDS = 5

simulated_drift = 0.5

CERT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/cert.pem")


def parse_args():
    parser = argparse.ArgumentParser(description="Secure clock sync client")
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Server IP or hostname (or set CLOCKSYNC_SERVER_IP env var)",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Server TCP port")
    parser.add_argument(
        "--server-hostname",
        default=None,
        help="TLS hostname for certificate verification (defaults to --host)",
    )
    parser.add_argument("--rounds", type=int, default=NUM_SYNCS, help="Number of sync rounds")
    parser.add_argument("--clients", type=int, default=1, help="Number of concurrent clients")
    return parser.parse_args()


def compute_drift_rate(samples):
    if len(samples) < 2:
        return 0.0

    x = [item["elapsed"] for item in samples]
    y = [item["offset"] for item in samples]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return 0.0

    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(samples)))
    return numerator / denominator


context = ssl.create_default_context()
context.load_verify_locations(CERT_FILE)

args = parse_args()
host = args.host
port = args.port
server_hostname = args.server_hostname or host
num_rounds = args.rounds
num_clients = max(1, args.clients)
print_lock = threading.Lock()


def run_client_session(client_id):
    samples = []
    session_start_monotonic = time.monotonic()

    with print_lock:
        print(f"\n[Client {client_id}] Starting Secure Clock Synchronization...")
        print(f"[Client {client_id}] Target server: {host}:{port}")
        print(f"[Client {client_id}] TLS hostname verification: {server_hostname}\n")

    for i in range(num_rounds):
        request_id = i + 1

        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(SOCKET_TIMEOUT_SECONDS)
            secure_socket = context.wrap_socket(client_socket, server_hostname=server_hostname)
            secure_socket.connect((host, port))

            t1 = time.time() + simulated_drift
            request = {"type": "TIME_REQUEST", "id": request_id, "T1": t1}
            secure_socket.sendall(json.dumps(request).encode())

            data = secure_socket.recv(BUFFER_SIZE)
            t4 = time.time() + simulated_drift

            response = json.loads(data.decode())
            if response.get("type") != "TIME_REPLY":
                raise ValueError("Invalid response type")
            if response.get("id") != request_id:
                raise ValueError("Mismatched response id")

            t2 = response["T2"]
            t3 = response["T3"]

            offset = ((t2 - t1) + (t3 - t4)) / 2
            delay = (t4 - t1) - (t3 - t2)

            sample = {
                "round": request_id,
                "offset": offset,
                "delay": delay,
                "elapsed": time.monotonic() - session_start_monotonic,
            }
            samples.append(sample)

            with print_lock:
                print(f"[Client {client_id}] Round {request_id}")
                print(f"[Client {client_id}] Offset: {offset:.6f}")
                print(f"[Client {client_id}] Delay : {delay:.6f}\n")

            secure_socket.close()

        except ConnectionRefusedError as e:
            with print_lock:
                print(f"[Client {client_id}] Round {request_id} failed: {e}")
                print("Hint: Start secure_server.py on the server device, verify IP/port, and allow TCP port in firewall.\n")

        except (socket.timeout, ssl.SSLError, OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            with print_lock:
                print(f"[Client {client_id}] Round {request_id} failed: {e}\n")

        time.sleep(REQUEST_INTERVAL_SECONDS)

    if samples:
        offsets = [sample["offset"] for sample in samples]
        delays = [sample["delay"] for sample in samples]
        min_delay_index = delays.index(min(delays))
        best_offset = offsets[min_delay_index]
        drift_rate = compute_drift_rate(samples)

        now_monotonic = time.monotonic()
        elapsed_now = now_monotonic - session_start_monotonic
        drift_corrected_offset = best_offset + (drift_rate * elapsed_now)

        drifted_now = time.time() + simulated_drift
        corrected_time = drifted_now + drift_corrected_offset
        real_time = time.time()

        baseline_error = abs(drifted_now - real_time)
        corrected_error = abs(corrected_time - real_time)
        improvement = 0.0
        if baseline_error > 0:
            improvement = ((baseline_error - corrected_error) / baseline_error) * 100

        with print_lock:
            print(f"----- Client {client_id} Secure Synchronization Result -----")
            print(f"Successful Rounds: {len(samples)}/{num_rounds}")
            print(f"Best Offset (min delay sample): {best_offset:.6f}")
            print(f"Average Offset: {statistics.mean(offsets):.6f}")
            print(f"Minimum Delay: {min(delays):.6f}")
            if len(delays) > 1:
                print(f"Delay Jitter (stdev): {statistics.pstdev(delays):.6f}")
            else:
                print("Delay Jitter (stdev): 0.000000")

            print("\n----- Drift Correction -----")
            print(f"Estimated Drift Rate: {drift_rate:.9f} sec/sec")
            print(f"Offset Used For Correction: {drift_corrected_offset:.6f}")

            print("\n----- Accuracy Evaluation -----")
            print(f"Error Before Correction: {baseline_error:.6f} seconds")
            print(f"Error After Correction : {corrected_error:.6f} seconds")
            print(f"Improvement            : {improvement:.2f}%\n")
    else:
        with print_lock:
            print(f"[Client {client_id}] No successful synchronization rounds.\n")


if num_clients == 1:
    run_client_session(1)
else:
    workers = []
    for client_id in range(1, num_clients + 1):
        thread = threading.Thread(target=run_client_session, args=(client_id,), daemon=False)
        workers.append(thread)
        thread.start()

    for worker in workers:
        worker.join()
