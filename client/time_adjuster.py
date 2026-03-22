import time


def corrected_time(local_drift_seconds: float, offset: float) -> float:
    return time.time() + local_drift_seconds + offset


def error_against_reference(local_drift_seconds: float, offset: float, reference_time: float) -> float:
    return abs(corrected_time(local_drift_seconds, offset) - reference_time)
