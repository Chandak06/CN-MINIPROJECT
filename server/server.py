import json
import random
import socket
import threading
import time

HOST = "0.0.0.0"
PORT = 5005
BUFFER_SIZE = 1024

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))

print("Distributed Clock Synchronization Server Running...")
print(f"Listening on {HOST}:{PORT}\n")


def parse_request(data):
    """Accept JSON requests and keep legacy TIME_REQUEST compatibility."""
    try:
        payload = json.loads(data.decode())
        if payload.get("type") == "TIME_REQUEST":
            return payload.get("id")
        return None
    except (json.JSONDecodeError, UnicodeDecodeError):
        if data == b"TIME_REQUEST":
            return None
        return None


def handle_client(data, addr, t2):
    try:
        request_id = parse_request(data)
        if request_id is None and data != b"TIME_REQUEST":
            return

        time.sleep(random.uniform(0.001, 0.005))
        t3 = time.time()

        response = {
            "type": "TIME_REPLY",
            "id": request_id,
            "T2": t2,
            "T3": t3,
        }
        server_socket.sendto(json.dumps(response).encode(), addr)
        print(f"Responded to {addr} (id={request_id})")

    except Exception as e:
        print(f"Error handling client {addr}: {e}")


while True:
    data, addr = server_socket.recvfrom(BUFFER_SIZE)
    t2 = time.time()
    print(f"Request received from {addr}")

    client_thread = threading.Thread(
        target=handle_client,
        args=(data, addr, t2),
        daemon=True,
    )
    client_thread.start()
