"""Secure TLS/TCP Time-Sync Server (primary mode)

Transport: TCP (SOCK_STREAM) wrapped in TLS via ssl.SSLContext.
Default port: 6000

TLS requires a reliable, ordered byte stream — hence TCP rather than UDP.
The T1–T4 timestamp exchange fully accounts for the TCP round-trip, so
offset and delay measurements remain accurate.

Requires security/cert.pem + security/key.pem (run generate_cert.py first).
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
import random
import socket
import ssl
import sys
import threading
import time

SERVER_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SERVER_DIR)
if SERVER_DIR not in sys.path:
    sys.path.append(SERVER_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from time_manager import MasterClock
from ntp_sync import PRIMARY_NTP_SERVER
from utils.packet_format import (
    build_time_reply,
    decode_packet,
    encode_packet,
    validate_request,
)

HOST = "0.0.0.0"
PORT = 6000
BUFFER_SIZE = 2048

CERT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/cert.pem")
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/key.pem")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Secure TLS time sync server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--ntp-server", default=PRIMARY_NTP_SERVER)
    parser.add_argument("--max-workers", type=int, default=max(8, (os.cpu_count() or 1) * 4))
    parser.add_argument("--max-queue", type=int, default=100)
    parser.add_argument("--backlog", type=int, default=50)
    parser.add_argument("--accept-timeout", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((args.host, args.port))
    server_socket.listen(max(1, args.backlog))
    server_socket.settimeout(max(0.1, args.accept_timeout))

    clock = MasterClock(ntp_server=args.ntp_server)
    clock.start()

    print("Secure Clock Synchronization Server Running...")
    print(f"Listening on {args.host}:{args.port}")
    print(f"Thread pool: workers={args.max_workers}, queue={args.max_queue}, backlog={args.backlog}")

    # Limit in-flight + queued requests to avoid unbounded memory/thread growth under stress.
    pending_slots = threading.BoundedSemaphore(max(1, args.max_workers + args.max_queue))

    def handle_client(conn: ssl.SSLSocket, addr: tuple[str, int]) -> None:
        try:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                return

            t2 = clock.now()  # Capture T2 immediately after receive, before any processing
            packet = decode_packet(data)
            validate_request(packet)
            request_id = int(packet["id"])

            time.sleep(random.uniform(0.001, 0.005))
            t3 = clock.now()
            response = build_time_reply(
                request_id=request_id,
                t2=t2,
                t3=t3,
                reference_time=clock.now(),
                time_source=clock.status(),
            )
            conn.sendall(encode_packet(response))
            print(f"Responded to {addr} id={request_id} source={clock.status()}")
        except Exception as exc:
            print(f"Client error ({addr}): {exc}")
        finally:
            conn.close()
            pending_slots.release()

    try:
        with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
            while True:
                try:
                    client_socket, addr = server_socket.accept()
                except socket.timeout:
                    continue

                if not pending_slots.acquire(blocking=False):
                    print(f"Overloaded, dropping connection from {addr}")
                    client_socket.close()
                    continue

                try:
                    secure_conn = context.wrap_socket(client_socket, server_side=True)
                except (ssl.SSLError, OSError) as exc:
                    message = str(exc)
                    # Plain TCP health checks (without TLS handshake) can cause benign EOF here.
                    if "UNEXPECTED_EOF_WHILE_READING" not in message:
                        print(f"TLS handshake failed for {addr}: {exc}")
                    client_socket.close()
                    pending_slots.release()
                    continue

                try:
                    pool.submit(handle_client, secure_conn, addr)
                except RuntimeError:
                    print("Worker pool is shutting down; rejecting new connection")
                    secure_conn.close()
                    pending_slots.release()
    except KeyboardInterrupt:
        print("\nSecure server stopped by user.")
    finally:
        clock.stop()
        server_socket.close()


if __name__ == "__main__":
    main()
