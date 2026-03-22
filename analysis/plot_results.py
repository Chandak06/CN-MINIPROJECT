import argparse
import csv
from typing import List

import matplotlib.pyplot as plt


def read_series(csv_path: str) -> tuple[List[float], List[float], List[float]]:
    rounds: List[float] = []
    offsets: List[float] = []
    delays: List[float] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            rounds.append(float(row["round"]))
            offsets.append(float(row["offset"]))
            delays.append(float(row["delay"]))
    return rounds, offsets, delays


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot sync delay/offset trends")
    parser.add_argument("--input", required=True, help="Path to sync_data.csv")
    parser.add_argument("--output", default=None, help="Optional output image path")
    args = parser.parse_args()

    rounds, offsets, delays = read_series(args.input)
    if not rounds:
        print("No data to plot.")
        return

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)

    axes[0].plot(rounds, offsets, marker="o", color="#1f77b4")
    axes[0].set_ylabel("Offset (s)")
    axes[0].set_title("Clock Offset Trend")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(rounds, delays, marker="s", color="#d62728")
    axes[1].set_xlabel("Round")
    axes[1].set_ylabel("Delay (s)")
    axes[1].set_title("Network Delay Trend")
    axes[1].grid(True, alpha=0.3)

    fig.tight_layout()

    if args.output:
        fig.savefig(args.output, dpi=150)
        print(f"Saved plot to: {args.output}")
    else:
        plt.show()


if __name__ == "__main__":
    main()
