"""UDP Time-Sync Server (demo / unencrypted mode)

Transport: UDP (SOCK_DGRAM) — no TLS, no authentication.
Default port: 5005

This server is provided as a lightweight alternative for testing on a
trusted local network. For secure deployments use secure_server.py, which
wraps the same MasterClock over a TLS/TCP connection.
"""
import argparse
import os
import random
import socket
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
from utils.packet_format import (
    build_time_reply,
    decode_packet,
    encode_packet,
    validate_request,
)


HOST = "0.0.0.0"
PORT = 5005
BUFFER_SIZE = 2048


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UDP time sync server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--ntp-server", default="time.google.com")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    clock = MasterClock(ntp_server=args.ntp_server)
    clock.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((args.host, args.port))

    print("Distributed Clock Synchronization UDP Server Running...")
    print(f"Listening on {args.host}:{args.port}")

    def handle_client(data: bytes, addr: tuple[str, int], t2: float) -> None:
        try:
            packet = decode_packet(data)
            validate_request(packet)
            request_id = int(packet["id"])

            time.sleep(random.uniform(0.001, 0.005))
            t3 = clock.now()
            reply = build_time_reply(
                request_id=request_id,
                t2=t2,
                t3=t3,
                reference_time=clock.now(),
                time_source=clock.status(),
            )
            server_socket.sendto(encode_packet(reply), addr)
            print(f"Responded to {addr} id={request_id} source={clock.status()}")
        except Exception as exc:
            print(f"Error handling request from {addr}: {exc}")

    try:
        while True:
            data, addr = server_socket.recvfrom(BUFFER_SIZE)
            t2 = clock.now()
            worker = threading.Thread(target=handle_client, args=(data, addr, t2), daemon=True)
            worker.start()
    except KeyboardInterrupt:
        print("\nServer stopped by user.")
    finally:
        clock.stop()
        server_socket.close()


if __name__ == "__main__":
    main()
