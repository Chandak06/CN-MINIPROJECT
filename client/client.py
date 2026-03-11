import socket        # Provides UDP socket for sending and receiving datagrams
import time          # Used to record timestamps T1 and T4 with high precision
import json          # Used to parse the JSON response received from the server
import statistics    # Used to compute the mean (average) of collected offsets

SERVER_IP = "127.0.0.1"   # IP address of the NTP server to synchronize with
SERVER_PORT = 5005         # UDP port the server is listening on
BUFFER_SIZE = 1024         # Maximum bytes to read from a single server response
NUM_SYNCS = 10             # Number of synchronization rounds to perform

# Create a UDP socket (SOCK_DGRAM = connectionless, no handshake)
client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Set a 3-second timeout: if the server does not reply within 3 seconds,
# a socket.timeout exception is raised so the round is skipped gracefully
client_socket.settimeout(3)

offsets = []   # Stores the calculated clock offset from each successful round
delays  = []   # Stores the round-trip delay from each successful round

# Simulated clock drift: pretend this client's clock is 0.5 seconds AHEAD of real time
# This is added to T1 and T4 to mimic a client with an inaccurate local clock
simulated_drift = 0.5

print("Starting Clock Synchronization...\n")

# Run NUM_SYNCS rounds of the NTP 4-timestamp exchange
for i in range(NUM_SYNCS):

    try:
        # ── NTP Timestamp T1 ──────────────────────────────────────────────────
        # T1 = client's local time (with drift applied) just before sending the request
        # Adding simulated_drift mimics what a drifted clock would report
        T1 = time.time() + simulated_drift

        # Send the time request datagram to the server
        client_socket.sendto(b"TIME_REQUEST", (SERVER_IP, SERVER_PORT))

        # Block and wait for the server's response datagram (up to BUFFER_SIZE bytes)
        data, _ = client_socket.recvfrom(BUFFER_SIZE)

        # ── NTP Timestamp T4 ──────────────────────────────────────────────────
        # T4 = client's local time (with drift applied) immediately after receiving the reply
        T4 = time.time() + simulated_drift

        # Decode the JSON response and extract the two server-side timestamps
        response = json.loads(data.decode())

        T2 = response["T2"]   # Time the server received the request (from server clock)
        T3 = response["T3"]   # Time the server sent the response  (from server clock)

        # ── NTP Offset Formula ────────────────────────────────────────────────
        # offset θ = ((T2 - T1) + (T3 - T4)) / 2
        # Positive offset → client clock is BEHIND the server
        # Negative offset → client clock is AHEAD of the server
        offset = ((T2 - T1) + (T3 - T4)) / 2

        # ── NTP Round-Trip Delay Formula ──────────────────────────────────────
        # delay δ = (T4 - T1) - (T3 - T2)
        # Total elapsed time on client side minus processing time on server side
        delay = (T4 - T1) - (T3 - T2)

        offsets.append(offset)   # Store this round's offset for later analysis
        delays.append(delay)     # Store this round's delay for later analysis

        print(f"Round {i+1}")
        print(f"Offset: {offset:.6f}")
        print(f"Delay : {delay:.6f}\n")

        # Wait 1 second between rounds to avoid flooding the server
        time.sleep(1)

    except socket.timeout:
        # Server did not respond within 3 seconds; skip this round
        print("Server timeout\n")

# Close the UDP socket once all rounds are complete
client_socket.close()

# Only compute results if at least one round succeeded
if offsets:

    # The best offset estimate is the one from the round with the LOWEST delay
    # A lower delay means less network jitter, so that sample is most accurate
    min_delay_index = delays.index(min(delays))
    best_offset = offsets[min_delay_index]

    print("----- Synchronization Result -----")
    print(f"Best Offset (min delay sample): {best_offset:.6f}")   # Most accurate offset
    print(f"Average Offset: {statistics.mean(offsets):.6f}")       # Mean across all rounds
    print(f"Minimum Delay: {min(delays):.6f}")                     # Lowest observed RTT

    # ── Clock Correction ──────────────────────────────────────────────────────
    # Apply the best_offset to the current drifted time to get the corrected time
    # corrected_time ≈ true server time
    corrected_time = (time.time() + simulated_drift) + best_offset

    # real_time = what time.time() actually is (ground truth in this simulation)
    real_time = time.time()

    # Error = how far off the corrected time is from the true time
    # Ideally this should be very close to 0
    error = abs(corrected_time - real_time)

    print("\n----- Accuracy Evaluation -----")
    print(f"Corrected Time Error: {error:.6f} seconds")

else:
    # All rounds timed out — no data to analyse
    print("No successful synchronization rounds.")
