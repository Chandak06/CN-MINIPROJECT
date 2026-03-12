import json
import socket
import statistics
import time

SERVER_IP = "192.168.56.1"
SERVER_PORT = 5005
BUFFER_SIZE = 1024
NUM_SYNCS = 10
REQUEST_INTERVAL_SECONDS = 1
SOCKET_TIMEOUT_SECONDS = 3

simulated_drift = 0.5


def compute_drift_rate(samples):
    """Estimate drift rate as slope(offset vs elapsed time) in seconds/second."""
    if len(samples) < 2:
        return 0.0

    x = [item["elapsed"] for item in samples]
    y = [item["offset"] for item in samples]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return 0.0

    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(len(samples)))
    return numerator / denominator


client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client_socket.settimeout(SOCKET_TIMEOUT_SECONDS)

samples = []
session_start_monotonic = time.monotonic()

print("Starting Clock Synchronization...\n")

for i in range(NUM_SYNCS):
    request_id = i + 1

    try:
        t1 = time.time() + simulated_drift
        request = {"type": "TIME_REQUEST", "id": request_id, "T1": t1}
        client_socket.sendto(json.dumps(request).encode(), (SERVER_IP, SERVER_PORT))

        data, _ = client_socket.recvfrom(BUFFER_SIZE)
        t4 = time.time() + simulated_drift

        response = json.loads(data.decode())
        if response.get("type") != "TIME_REPLY":
            raise ValueError("Invalid response type")
        if response.get("id") != request_id:
            raise ValueError("Mismatched response id")

        t2 = response["T2"]
        t3 = response["T3"]

        offset = ((t2 - t1) + (t3 - t4)) / 2
        delay = (t4 - t1) - (t3 - t2)

        sample = {
            "round": request_id,
            "offset": offset,
            "delay": delay,
            "elapsed": time.monotonic() - session_start_monotonic,
        }
        samples.append(sample)

        print(f"Round {request_id}")
        print(f"Offset: {offset:.6f}")
        print(f"Delay : {delay:.6f}\n")

    except (socket.timeout, json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Round {request_id} failed: {e}\n")

    time.sleep(REQUEST_INTERVAL_SECONDS)

client_socket.close()

if samples:
    offsets = [sample["offset"] for sample in samples]
    delays = [sample["delay"] for sample in samples]
    min_delay_index = delays.index(min(delays))
    best_offset = offsets[min_delay_index]
    drift_rate = compute_drift_rate(samples)

    now_monotonic = time.monotonic()
    elapsed_now = now_monotonic - session_start_monotonic
    drift_corrected_offset = best_offset + (drift_rate * elapsed_now)

    drifted_now = time.time() + simulated_drift
    corrected_time = drifted_now + drift_corrected_offset
    real_time = time.time()

    baseline_error = abs(drifted_now - real_time)
    corrected_error = abs(corrected_time - real_time)
    improvement = 0.0
    if baseline_error > 0:
        improvement = ((baseline_error - corrected_error) / baseline_error) * 100

    print("----- Synchronization Result -----")
    print(f"Successful Rounds: {len(samples)}/{NUM_SYNCS}")
    print(f"Best Offset (min delay sample): {best_offset:.6f}")
    print(f"Average Offset: {statistics.mean(offsets):.6f}")
    print(f"Minimum Delay: {min(delays):.6f}")
    if len(delays) > 1:
        print(f"Delay Jitter (stdev): {statistics.pstdev(delays):.6f}")
    else:
        print("Delay Jitter (stdev): 0.000000")

    print("\n----- Drift Correction -----")
    print(f"Estimated Drift Rate: {drift_rate:.9f} sec/sec")
    print(f"Offset Used For Correction: {drift_corrected_offset:.6f}")

    print("\n----- Accuracy Evaluation -----")
    print(f"Error Before Correction: {baseline_error:.6f} seconds")
    print(f"Error After Correction : {corrected_error:.6f} seconds")
    print(f"Improvement            : {improvement:.2f}%")
else:
    print("No successful synchronization rounds.")
