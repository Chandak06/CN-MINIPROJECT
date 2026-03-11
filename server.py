# server.py

import socket
import time
import json
import random

HOST = "127.0.0.1"   # Use localhost for Windows safety
PORT = 5005         # Changed port to avoid conflicts

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((HOST, PORT))

print("Distributed Clock Synchronization Server Running...")
print(f"Listening on {HOST}:{PORT}\n")

while True:
    try:
        data, addr = server_socket.recvfrom(1024)

        if not data:
            continue

        # T2: Server receive time
        T2 = time.time()

        # Simulate small processing delay
        time.sleep(random.uniform(0.001, 0.005))

        # T3: Server send time
        T3 = time.time()

        response = {
            "T2": T2,
            "T3": T3
        }

        server_socket.sendto(json.dumps(response).encode(), addr)

    except Exception as e:
        print("Server Error:", e)