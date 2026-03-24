import argparse
import csv
import os
import socket
import ssl
import statistics
import sys
import time
from typing import Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CLIENT_DIR not in sys.path:
    sys.path.append(CLIENT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from sync_algorithm import compute_offset_and_delay
from time_adjuster import corrected_time
from utils.packet_format import (
    build_time_request,
    decode_packet,
    encode_packet,
    validate_reply,
)


DEFAULT_HOST = os.getenv("CLOCKSYNC_SERVER_IP", "127.0.0.1")
DEFAULT_PORT = 6000
REQUEST_INTERVAL_SECONDS = 1.0
BUFFER_SIZE = 2048
SOCKET_TIMEOUT_SECONDS = 5
DEFAULT_ROUNDS = 10
DEFAULT_RESULTS = os.path.join(PROJECT_ROOT, "results", "sync_data.csv")
CERT_FILE = os.path.join(PROJECT_ROOT, "security", "cert.pem")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Secure synchronization client")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--server-hostname", default=None)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--output", default=DEFAULT_RESULTS)
    return parser.parse_args()


def _format_timestamp(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) + f".{int((ts % 1) * 1000):03d}"


def _compute_corrected_offset(samples: List[Dict[str, float]]) -> float:
    """Compute corrected offset using mean offset from all samples."""
    if not samples:
        return 0.0
    offsets = [sample["offset"] for sample in samples]
    return statistics.mean(offsets)


def save_results(path: str, rows: List[Dict[str, float]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["round", "offset", "delay", "elapsed", "reference_time", "time_source"])
        writer.writeheader()
        writer.writerows(rows)


def run_session(host: str, port: int, server_hostname: str, rounds: int) -> List[Dict[str, float]]:
    context = ssl.create_default_context()
    context.load_verify_locations(CERT_FILE)

    samples: List[Dict[str, float]] = []
    start_monotonic = time.monotonic()

    for request_id in range(1, rounds + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as raw_socket:
            raw_socket.settimeout(SOCKET_TIMEOUT_SECONDS)
            with context.wrap_socket(raw_socket, server_hostname=server_hostname) as secure_socket:
                secure_socket.connect((host, port))

                t1 = time.time()
                request = build_time_request(request_id=request_id, t1=t1)
                secure_socket.sendall(encode_packet(request))

                response_data = secure_socket.recv(BUFFER_SIZE)
                t4 = time.time()

                packet = decode_packet(response_data)
                validate_reply(packet)

                if packet["id"] != request_id:
                    raise ValueError("Response ID does not match request ID")

                sync_values = compute_offset_and_delay(t1=t1, t2=packet["T2"], t3=packet["T3"], t4=t4)
                sample = {
                    "round": request_id,
                    "offset": sync_values["offset"],
                    "delay": sync_values["delay"],
                    "elapsed": time.monotonic() - start_monotonic,
                    "reference_time": packet["reference_time"],
                    "time_source": packet.get("time_source", "unknown"),
                }
                samples.append(sample)

                print(
                    f"Round {request_id}: offset={sample['offset']:.6f}s delay={sample['delay']:.6f}s source={sample['time_source']}"
                )

        time.sleep(REQUEST_INTERVAL_SECONDS)

    return samples


def print_summary(samples: List[Dict[str, float]]) -> None:
    if not samples:
        print("No successful synchronization samples were collected.")
        return

    offsets = [sample["offset"] for sample in samples]
    delays = [sample["delay"] for sample in samples]
    mean_offset = statistics.mean(offsets)
    mean_delay = statistics.mean(delays)
    min_delay = min(delays)
    max_delay = max(delays)
    
    corrected_offset = _compute_corrected_offset(samples)

    raw_local_time = time.time()
    corrected_local_time = corrected_time(local_drift_seconds=0.0, offset=corrected_offset)
    reference_time = samples[-1]["reference_time"]
    source = str(samples[-1].get("time_source", "unknown"))

    baseline_error = abs(raw_local_time - reference_time)
    corrected_error = abs(corrected_local_time - reference_time)
    improvement = 0.0
    if baseline_error > 0:
        improvement = ((baseline_error - corrected_error) / baseline_error) * 100

    print("\n--- Synchronization Summary ---")
    print(f"Samples collected: {len(samples)}")
    print(f"Mean offset: {mean_offset:.6f}s")
    print(f"Offset range: {min(offsets):.6f}s to {max(offsets):.6f}s")
    print(f"Mean delay: {mean_delay:.6f}s")
    print(f"Delay range: {min_delay:.6f}s to {max_delay:.6f}s")
    print(f"Server time source: {source}")
    print(f"Error before correction: {baseline_error:.6f}s")
    print(f"Error after correction: {corrected_error:.6f}s")
    print(f"Improvement: {improvement:.2f}%")
    print(f"Server time (last reply): {_format_timestamp(reference_time)}")
    print(f"Client corrected time   : {_format_timestamp(corrected_local_time)}")
    print(f"Difference after correction: {abs(corrected_local_time - reference_time):.6f}s")


def main() -> None:
    args = parse_args()
    server_hostname = args.server_hostname or args.host
    try:
        samples = run_session(
            host=args.host,
            port=args.port,
            server_hostname=server_hostname,
            rounds=max(1, args.rounds),
        )
    except ConnectionRefusedError:
        print(
            f"ERROR: Connection refused — the server is not running on "
            f"{args.host}:{args.port}. Start it with:\n"
            f"  python server/secure_server.py --host 0.0.0.0 --port {args.port}"
        )
        sys.exit(1)
    except socket.timeout:
        print(
            f"ERROR: Connection timed out — "
            f"{args.host}:{args.port} did not respond within {SOCKET_TIMEOUT_SECONDS}s. "
            f"Check the host/port and any firewall rules."
        )
        sys.exit(1)
    except ssl.SSLError as exc:
        print(f"ERROR: TLS handshake failed — {exc}")
        sys.exit(1)
    except OSError as exc:
        print(f"ERROR: Network error — {exc}")
        sys.exit(1)
    save_results(args.output, samples)
    print_summary(samples)


if __name__ == "__main__":
    main()
