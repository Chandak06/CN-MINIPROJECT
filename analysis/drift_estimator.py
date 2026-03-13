import argparse
import csv
from typing import Dict, List


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


def estimate_drift_rate(samples: List[Dict[str, float]]) -> float:
    if len(samples) < 2:
        return 0.0

    x = [item["elapsed"] for item in samples]
    y = [item["offset"] for item in samples]
    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)

    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return 0.0

    numerator = sum((x[idx] - x_mean) * (y[idx] - y_mean) for idx in range(len(samples)))
    return numerator / denominator


def main() -> None:
    parser = argparse.ArgumentParser(description="Estimate drift rate from synchronization CSV")
    parser.add_argument("--input", required=True, help="Path to sync_data.csv")
    args = parser.parse_args()

    samples = read_samples(args.input)
    drift = estimate_drift_rate(samples)
    print(f"Estimated drift rate: {drift:.9f} sec/sec")


if __name__ == "__main__":
    main()
