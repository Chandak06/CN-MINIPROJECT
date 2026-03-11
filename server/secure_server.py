import os            # Used to build file paths relative to this script's location
import socket        # Provides TCP socket interface for accepting client connections
import ssl           # Python's built-in TLS/SSL wrapper for encrypting the TCP connection
import threading     # Allows each client connection to be handled in its own thread
import time          # Used to record timestamps T2 and T3 with high precision
import json          # Used to serialize the response dictionary to a JSON string
import random        # Used to simulate a random processing delay between T2 and T3

HOST = "127.0.0.1"  # Bind to localhost; only accepts local connections
PORT = 6000          # TCP port for the secure (TLS) server — different from the plain server (5005)
BUFFER_SIZE = 1024   # Maximum bytes to read in a single recv() call

# Build absolute paths to cert and key files relative to this script's location
# os.path.dirname(__file__) = directory of this script (server/)
# ../security/ = one level up then into security/
CERT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/cert.pem")
KEY_FILE  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/key.pem")

# Create a TLS context configured for server-side operation
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)

# Load the server's certificate and private key into the TLS context
# The certificate proves the server's identity to connecting clients
context.load_cert_chain(certfile=CERT_FILE, keyfile=KEY_FILE)

# Create a standard TCP socket (SOCK_STREAM = connection-oriented, reliable)
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Allow the port to be reused immediately after the server stops,
# preventing "Address already in use" errors on restart
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind the socket to the address and port so it is ready to accept connections
server_socket.bind((HOST, PORT))

# Start listening; 20 = maximum number of pending connections in the queue
# (higher value supports more simultaneous incoming connection attempts)
server_socket.listen(20)

print("Secure Clock Synchronization Server Running...")
print(f"Listening on {HOST}:{PORT}\n")


# This function handles a single connected client in its own thread
# conn — the TLS-wrapped socket for this client
# addr — (ip, port) of the connected client
def handle_client(conn, addr):
    try:
        print(f"Secure client connected: {addr}")

        # Receive up to BUFFER_SIZE bytes from the client over the encrypted connection
        data = conn.recv(BUFFER_SIZE)

        # T2: record receive timestamp IMMEDIATELY after data arrives,
        # before any decoding or validation — minimises timing error
        T2 = time.time()

        # If the client closed the connection without sending data, exit the thread
        if not data:
            return

        # Check that the received message is a valid NTP time request
        if data.decode() == "TIME_REQUEST":

            # Simulate a small random processing delay (1–5 ms)
            # Represents real-world time the server takes to prepare its response
            time.sleep(random.uniform(0.001, 0.005))

            # T3: record the exact time the server is about to send the reply
            T3 = time.time()

            # Build the response with both server-side timestamps
            response = {"T2": T2, "T3": T3}

            # Send the JSON-encoded timestamps to the client over the TLS connection
            conn.send(json.dumps(response).encode())

            print(f"Responded to {addr}")

    except Exception as e:
        # Catch all errors (SSL errors, decode errors, broken pipe, etc.)
        # and log them without crashing the server
        print(f"Client error ({addr}): {e}")

    finally:
        # Always close the connection when done, whether successful or not
        # This releases the file descriptor and frees resources
        conn.close()


# Main loop: continuously accept new client connections
while True:

    # Block until a client connects; returns a raw TCP socket and the client's address
    client_socket, addr = server_socket.accept()

    try:
        # Upgrade the raw TCP socket to a TLS-encrypted socket using our server context
        # server_side=True means this end presents the certificate and does the TLS handshake
        secure_conn = context.wrap_socket(client_socket, server_side=True)

    except ssl.SSLError as e:
        # If TLS handshake fails (e.g. client sent non-TLS data), log and skip this client
        # This prevents one bad client from crashing the entire server
        print(f"SSL handshake failed for {addr}: {e}")
        client_socket.close()   # Close the raw socket to free resources
        continue                # Go back to waiting for the next connection

    # Spawn a dedicated thread for this client so other clients are not blocked
    # daemon=True ensures the thread is cleaned up automatically when the server exits
    thread = threading.Thread(target=handle_client, args=(secure_conn, addr), daemon=True)
    thread.start()              # Start handling the client in the background
