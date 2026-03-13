import argparse
import csv
import os
import sys
from typing import Dict, List

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from utils.statistics_tools import estimate_drift_rate  # noqa: E402


def read_samples(csv_path: str) -> List[Dict[str, float]]:
    samples: List[Dict[str, float]] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            samples.append(
                {
                    "offset": float(row["offset"]),
                    "elapsed": float(row["elapsed"]),
                }
            )
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate drift rate from synchronization CSV")
    parser.add_argument("--input", required=True, help="Path to sync_data.csv")
    args = parser.parse_args()

    samples = read_samples(args.input)
    drift = estimate_drift_rate(samples)
    print(f"Estimated drift rate: {drift:.9f} sec/sec")


if __name__ == "__main__":
    main()
