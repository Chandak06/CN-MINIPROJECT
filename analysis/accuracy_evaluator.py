import argparse
import csv
import statistics
from typing import Dict, List


def read_samples(csv_path: str) -> List[Dict[str, float]]:
    rows: List[Dict[str, float]] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            rows.append(
                {
                    "offset": float(row["offset"]),
                    "delay": float(row["delay"]),
                }
            )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate synchronization accuracy from CSV")
    parser.add_argument("--input", required=True, help="Path to sync_data.csv")
    args = parser.parse_args()

    samples = read_samples(args.input)
    if not samples:
        print("No samples available.")
        return

    offsets = [row["offset"] for row in samples]
    delays = [row["delay"] for row in samples]

    print("--- Accuracy Metrics ---")
    print(f"Samples      : {len(samples)}")
    print(f"Mean Offset  : {statistics.mean(offsets):.6f}s")
    print(f"Offset Std   : {statistics.pstdev(offsets) if len(offsets) > 1 else 0.0:.6f}s")
    print(f"Mean Delay   : {statistics.mean(delays):.6f}s")
    print(f"Delay Std    : {statistics.pstdev(delays) if len(delays) > 1 else 0.0:.6f}s")
    print(f"Min Delay    : {min(delays):.6f}s")


if __name__ == "__main__":
    main()
