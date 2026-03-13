from typing import Dict, List
import statistics


Sample = Dict[str, float]


def pick_best_sample_by_delay(samples: List[Sample]) -> Sample:
    if not samples:
        raise ValueError("No samples provided")
    return min(samples, key=lambda item: item["delay"])


def estimate_drift_rate(samples: List[Sample]) -> float:
    if len(samples) < 2:
        return 0.0

    x = [item["elapsed"] for item in samples]
    y = [item["offset"] for item in samples]
    x_mean = statistics.mean(x)
    y_mean = statistics.mean(y)

    denominator = sum((value - x_mean) ** 2 for value in x)
    if denominator == 0:
        return 0.0

    numerator = sum((x[idx] - x_mean) * (y[idx] - y_mean) for idx in range(len(samples)))
    return numerator / denominator


def summarize_offsets(samples: List[Sample]) -> Dict[str, float]:
    offsets = [item["offset"] for item in samples]
    return {
        "mean_offset": statistics.mean(offsets),
        "min_offset": min(offsets),
        "max_offset": max(offsets),
        "offset_std": statistics.pstdev(offsets) if len(offsets) > 1 else 0.0,
    }


def summarize_delays(samples: List[Sample]) -> Dict[str, float]:
    delays = [item["delay"] for item in samples]
    return {
        "mean_delay": statistics.mean(delays),
        "min_delay": min(delays),
        "max_delay": max(delays),
        "delay_std": statistics.pstdev(delays) if len(delays) > 1 else 0.0,
    }
