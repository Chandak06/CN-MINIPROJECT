# client.py

import socket
import time
import json
import statistics

SERVER_IP = "127.0.0.1"
SERVER_PORT = 5005
NUM_SYNCS = 10

client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(3)

offsets = []
delays = []

# Simulated clock drift (client clock is ahead by 0.5 sec)
simulated_drift = 0.5

print("Starting Clock Synchronization...\n")

for i in range(NUM_SYNCS):

    try:
        # T1: Client send time
        T1 = time.time() + simulated_drift

        client_socket.sendto(b"TIME_REQUEST", (SERVER_IP, SERVER_PORT))

        data, _ = client_socket.recvfrom(1024)

        # T4: Client receive time
        T4 = time.time() + simulated_drift

        response = json.loads(data.decode())

        T2 = response["T2"]
        T3 = response["T3"]

        # Offset calculation
        offset = ((T2 - T1) + (T3 - T4)) / 2

        # Delay calculation
        delay = (T4 - T1) - (T3 - T2)

        offsets.append(offset)
        delays.append(delay)

        print(f"Round {i+1}")
        print(f"Offset: {offset:.6f} sec")
        print(f"Delay : {delay:.6f} sec\n")

        time.sleep(1)

    except socket.timeout:
        print("Server not responding. Check if server is running.\n")
        continue

    except ConnectionResetError:
        print("Connection reset. Server may not be running.\n")
        continue

if offsets:
    min_delay_index = delays.index(min(delays))
    best_offset = offsets[min_delay_index]

    print("----- Synchronization Result -----")
    print(f"Best Offset (min delay sample): {best_offset:.6f}")
    print(f"Average Offset: {statistics.mean(offsets):.6f}")
    print(f"Minimum Delay: {min(delays):.6f}")

    # Corrected time
    corrected_time = (time.time() + simulated_drift) + best_offset
    real_time = time.time()

    error = abs(corrected_time - real_time)

    print("\n----- Accuracy Evaluation -----")
    print(f"Corrected Time Error: {error:.6f} seconds")

else:
    print("No successful synchronization rounds.")