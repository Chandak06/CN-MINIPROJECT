from typing import Dict


def compute_offset_and_delay(t1: float, t2: float, t3: float, t4: float) -> Dict[str, float]:
    offset = ((t2 - t1) + (t3 - t4)) / 2
    delay = (t4 - t1) - (t3 - t2)
    return {
        "offset": offset,
        "delay": delay,
    }
