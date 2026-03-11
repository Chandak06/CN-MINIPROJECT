import socket        # Provides low-level network interface (UDP/TCP sockets)
import time          # Used to capture timestamps (T2, T3) with high precision
import json          # Used to encode the response dictionary into a string for transmission
import threading     # Allows handling multiple clients at the same time using threads
import random        # Used to simulate a random processing delay between T2 and T3

HOST = "127.0.0.1"  # Server binds to localhost (loopback); only accepts connections from the same machine
PORT = 5005          # UDP port the server listens on
BUFFER_SIZE = 1024   # Maximum bytes to read from a single UDP datagram

# Create a UDP socket (SOCK_DGRAM = datagram, connectionless — no handshake needed)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# SO_REUSEADDR lets the server restart immediately without waiting for the OS to
# release the port (avoids "Address already in use" error after a crash/restart)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind the socket to the host/port so it starts listening for incoming datagrams
server_socket.bind((HOST, PORT))

print("Distributed Clock Synchronization Server Running...")
print(f"Listening on {HOST}:{PORT}\n")


# This function runs in a separate thread for each client request
# data  — the raw bytes received from the client
# addr  — (ip, port) tuple identifying the client
# T2    — the timestamp recorded the instant the datagram arrived (passed from main loop)
def handle_client(data, addr, T2):
    try:
        # Decode the bytes to a string and check if it is a valid time request
        if data.decode() == "TIME_REQUEST":

            # Simulate a small random processing/network delay (1–5 ms)
            # This mimics real-world server processing time between receiving and sending
            time.sleep(random.uniform(0.001, 0.005))

            # T3: record the exact time the server is about to send the response
            T3 = time.time()

            # Build the response payload containing both server-side timestamps
            # T2 = when the server received the request
            # T3 = when the server sent the response
            response = {
                "T2": T2,
                "T3": T3
            }

            # Send the JSON-encoded response back to the specific client address
            server_socket.sendto(json.dumps(response).encode(), addr)

            print(f"Responded to {addr}")

    except Exception as e:
        # Catch any unexpected errors (e.g. decode failure) and log them
        # without crashing the thread or the entire server
        print(f"Error handling client {addr}: {e}")


# Main loop: runs forever, waiting for incoming UDP datagrams
while True:

    # Block until a datagram arrives; returns the raw data and the sender's address
    data, addr = server_socket.recvfrom(BUFFER_SIZE)

    # T2: capture the receive timestamp IMMEDIATELY after the datagram arrives,
    # before any processing, decoding, or thread creation — this is the most accurate T2
    T2 = time.time()

    print(f"Request received from {addr}")

    # Spawn a new thread to handle this client so the main loop can immediately
    # go back to waiting for the next request (supports multiple simultaneous clients)
    # daemon=True means the thread will be killed automatically when the main program exits
    client_thread = threading.Thread(
        target=handle_client,   # Function the thread will execute
        args=(data, addr, T2),  # Arguments passed to handle_client
        daemon=True             # Thread dies with the main process (clean shutdown)
    )
    client_thread.start()       # Start the thread execution
