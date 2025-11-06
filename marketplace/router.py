import json
from http import HTTPStatus
from typing import Any, Callable, Dict, Optional, Tuple


Handler = Callable[[Dict[str, Any], Dict[str, Any]], Tuple[int, Any]]


class Router:
    def __init__(self):
        self.routes: Dict[Tuple[str, str], Handler] = {}

    def add(self, method: str, path: str, handler: Handler) -> None:
        self.routes[(method.upper(), path)] = handler

    def resolve(self, method: str, path: str) -> Optional[Handler]:
        return self.routes.get((method.upper(), path))


def json_response(status: int, data: Any) -> Tuple[int, bytes, Dict[str, str]]:
    body = json.dumps(data, default=_serializer).encode("utf-8")
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Content-Length": str(len(body)),
        "Access-Control-Allow-Origin": "*",
    }
    return status, body, headers


def _serializer(value: Any):
    if isinstance(value, set):
        return list(value)
    if hasattr(value, "__dict__"):
        return value.__dict__
    return value


def parse_json_body(body: bytes) -> Dict[str, Any]:
    if not body:
        return {}
    return json.loads(body.decode("utf-8"))


def error_response(message: str, status: int = HTTPStatus.BAD_REQUEST) -> Tuple[int, bytes, Dict[str, str]]:
    return json_response(status, {"error": message})

