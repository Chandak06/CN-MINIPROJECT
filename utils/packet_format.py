import json
from typing import Any, Dict


TIME_REQUEST = "TIME_REQUEST"
TIME_REPLY = "TIME_REPLY"


def build_time_request(request_id: int, t1: float) -> Dict[str, Any]:
    return {
        "type": TIME_REQUEST,
        "id": request_id,
        "T1": t1,
    }


def build_time_reply(request_id: int, t2: float, t3: float, reference_time: float) -> Dict[str, Any]:
    return {
        "type": TIME_REPLY,
        "id": request_id,
        "T2": t2,
        "T3": t3,
        "reference_time": reference_time,
    }


def encode_packet(packet: Dict[str, Any]) -> bytes:
    return json.dumps(packet).encode("utf-8")


def decode_packet(data: bytes) -> Dict[str, Any]:
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Packet must decode to a JSON object")
    return payload


def validate_request(packet: Dict[str, Any]) -> None:
    if packet.get("type") != TIME_REQUEST:
        raise ValueError("Unsupported packet type")
    if "id" not in packet:
        raise ValueError("Request must include 'id'")
    if "T1" not in packet:
        raise ValueError("Request must include 'T1'")


def validate_reply(packet: Dict[str, Any]) -> None:
    if packet.get("type") != TIME_REPLY:
        raise ValueError("Unsupported packet type")
    for field in ("id", "T2", "T3", "reference_time"):
        if field not in packet:
            raise ValueError(f"Reply must include '{field}'")
