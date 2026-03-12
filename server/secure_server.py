import json
import os
import random
import socket
import ssl
import threading
import time

HOST = "0.0.0.0"
PORT = 6000
BUFFER_SIZE = 1024

CERT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/cert.pem")
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/key.pem")

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((HOST, PORT))
server_socket.listen(20)

print("Secure Clock Synchronization Server Running...")
print(f"Listening on {HOST}:{PORT}\n")


def parse_request(data):
    try:
        payload = json.loads(data.decode())
        if payload.get("type") == "TIME_REQUEST":
            return payload.get("id")
        return None
    except (json.JSONDecodeError, UnicodeDecodeError):
        if data == b"TIME_REQUEST":
            return None
        return None


def handle_client(conn, addr):
    try:
        print(f"Secure client connected: {addr}")
        data = conn.recv(BUFFER_SIZE)
        t2 = time.time()

        if not data:
            return

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
        conn.sendall(json.dumps(response).encode())
        print(f"Responded to {addr} (id={request_id})")

    except Exception as e:
        print(f"Client error ({addr}): {e}")

    finally:
        conn.close()


while True:
    client_socket, addr = server_socket.accept()

    try:
        secure_conn = context.wrap_socket(client_socket, server_side=True)
    except ssl.SSLError as e:
        print(f"SSL handshake failed for {addr}: {e}")
        client_socket.close()
        continue

    thread = threading.Thread(target=handle_client, args=(secure_conn, addr), daemon=True)
    thread.start()
