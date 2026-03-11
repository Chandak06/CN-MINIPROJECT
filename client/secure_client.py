import os            # Used to build the certificate path relative to this script
import socket        # Provides TCP socket for the underlying connection
import ssl           # Wraps the TCP socket with TLS encryption and certificate verification
import time          # Used to record timestamps T1 and T4 with high precision
import json          # Used to parse the JSON response received from the secure server
import statistics    # Used to compute the mean (average) of collected offsets

HOST = "192.168.56.1"   # LAN IP of the server machine — must match a SAN entry in the server's certificate
PORT = 6000           # TCP port the secure server is listening on
BUFFER_SIZE = 1024    # Maximum bytes to read from a single server response
NUM_SYNCS = 10        # Number of synchronization rounds to perform

# Simulated clock drift: pretend this client's clock is 0.5 seconds AHEAD of real time
# Same drift as the plain client so results are directly comparable
simulated_drift = 0.5

# Build the absolute path to the server's self-signed certificate
# This cert is used to verify the server's identity during TLS handshake
CERT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../security/cert.pem")

# Create a TLS context for client-side use
# ssl.create_default_context() sets secure defaults:
#   - verify_mode = CERT_REQUIRED  (server certificate MUST be verified)
#   - check_hostname = True        (cert hostname MUST match the server we connect to)
context = ssl.create_default_context()

# Load our self-signed certificate as a trusted Certificate Authority (CA)
# Without this, Python would reject the cert because it is not signed by a known CA
# This is the correct way to trust a self-signed cert — NOT by disabling verification
context.load_verify_locations(CERT_FILE)

offsets = []   # Stores the clock offset from each successful round
delays  = []   # Stores the round-trip delay from each successful round

print("Starting Secure Clock Synchronization...\n")

# Run NUM_SYNCS rounds of the NTP 4-timestamp exchange over TLS
for i in range(NUM_SYNCS):

    try:
        # Create a fresh TCP socket for each round
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Set a 5-second timeout for connect + send + recv operations
        client_socket.settimeout(5)

        # Upgrade the TCP socket to TLS using our context
        # server_hostname must match the cert's SAN or CN (cert has SAN: IP:127.0.0.1)
        # This value is used for certificate hostname verification (not for DNS resolution)
        secure_socket = context.wrap_socket(client_socket, server_hostname=HOST)

        # Perform the TCP + TLS handshake with the server
        # After this call the connection is fully encrypted and the server is authenticated
        secure_socket.connect((HOST, PORT))

        # ── NTP Timestamp T1 ──────────────────────────────────────────────────
        # T1 = client's local time (with drift) just before sending the request
        T1 = time.time() + simulated_drift

        # Send the time request over the encrypted TLS connection
        secure_socket.send(b"TIME_REQUEST")

        # Block and wait for the server's JSON response
        data = secure_socket.recv(BUFFER_SIZE)

        # ── NTP Timestamp T4 ──────────────────────────────────────────────────
        # T4 = client's local time (with drift) immediately after receiving the reply
        T4 = time.time() + simulated_drift

        # Parse the JSON response to extract the two server-side timestamps
        response = json.loads(data.decode())

        T2 = response["T2"]   # Time the server received the request (server clock)
        T3 = response["T3"]   # Time the server sent the response   (server clock)

        # ── NTP Offset Formula ────────────────────────────────────────────────
        # offset θ = ((T2 - T1) + (T3 - T4)) / 2
        # Accounts for asymmetric network delays in both directions
        offset = ((T2 - T1) + (T3 - T4)) / 2

        # ── NTP Round-Trip Delay Formula ──────────────────────────────────────
        # delay δ = (T4 - T1) - (T3 - T2)
        # Total round-trip time minus the time the server spent processing
        delay  = (T4 - T1) - (T3 - T2)

        offsets.append(offset)   # Save this round's offset result
        delays.append(delay)     # Save this round's delay result

        print(f"Round {i+1}")
        print(f"Offset: {offset:.6f}")
        print(f"Delay : {delay:.6f}\n")

        # Close the TLS connection for this round (a new one is opened next round)
        secure_socket.close()

    except (socket.timeout, ssl.SSLError, ConnectionRefusedError, OSError) as e:
        # Gracefully handle: server not running, TLS failure, network error, timeout
        # Print the failure and move on to the next round instead of crashing
        print(f"Round {i+1} failed: {e}\n")

    # Wait 1 second between rounds to avoid flooding the server
    time.sleep(1)

# Only compute results if at least one round succeeded
if offsets:

    # Choose the offset from the round with the minimum delay —
    # that round had the least network jitter so its offset is most reliable
    min_delay_index = delays.index(min(delays))
    best_offset = offsets[min_delay_index]

    print("----- Secure Synchronization Result -----")
    print(f"Best Offset (min delay sample): {best_offset:.6f}")   # Most accurate offset
    print(f"Average Offset: {statistics.mean(offsets):.6f}")       # Mean over all rounds
    print(f"Minimum Delay: {min(delays):.6f}")                     # Lowest observed RTT

    # ── Clock Correction ──────────────────────────────────────────────────────
    # Apply best_offset to the current drifted time to arrive at the corrected time
    corrected_time = (time.time() + simulated_drift) + best_offset

    # real_time is the ground truth (what time.time() truly is)
    real_time = time.time()

    # Error = absolute difference between corrected time and true time
    # A well-synchronised clock should produce an error very close to 0
    error = abs(corrected_time - real_time)

    print("\n----- Accuracy Evaluation -----")
    print(f"Corrected Time Error: {error:.6f} seconds")

else:
    # All rounds failed — nothing to report
    print("No successful synchronization rounds.")
