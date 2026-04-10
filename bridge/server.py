import json
import logging
from collections import deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Deque, Dict, Optional

from capture_session import CAPTURE_KIND_BY_PATH, CAPTURE_SESSION


LOGGER = logging.getLogger("deadbot.bridge")
EVENTS: Deque[Dict[str, Any]] = deque(maxlen=200)
SNAPSHOT: Dict[str, Any] = {}


class BridgeHandler(BaseHTTPRequestHandler):
    server_version = "DeadbotBridge/0.1"

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "events_received": len(EVENTS),
                    "last_snapshot_at": SNAPSHOT.get("updatedAt"),
                    "capture": CAPTURE_SESSION.status(),
                    "server_time": datetime.now(timezone.utc).isoformat(),
                },
            )
            return

        if self.path == "/capture/status":
            self._send_json(HTTPStatus.OK, CAPTURE_SESSION.status())
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path not in {"/events", "/snapshot", *CAPTURE_KIND_BY_PATH.keys()}:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return

        body = self._read_json_body()
        if body is None:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return

        if self.path == "/events":
            EVENTS.append(body)
            LOGGER.info("received event: %s", body.get("eventName") or body.get("type"))
            self._send_json(HTTPStatus.ACCEPTED, {"status": "accepted"})
            return

        if self.path == "/snapshot":
            SNAPSHOT.clear()
            SNAPSHOT.update(body)
            LOGGER.info("updated snapshot for steam_id=%s", body.get("steamId"))
            self._send_json(HTTPStatus.ACCEPTED, {"status": "accepted"})
            return

        capture_kind = CAPTURE_KIND_BY_PATH[self.path]
        CAPTURE_SESSION.append(capture_kind, body)
        LOGGER.info("captured raw payload: %s", capture_kind)
        self._send_json(HTTPStatus.ACCEPTED, {"status": "accepted"})

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.debug("%s - %s", self.address_string(), format % args)

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return None

        try:
            raw = self.rfile.read(content_length)
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    server = ThreadingHTTPServer(("127.0.0.1", 8765), BridgeHandler)
    LOGGER.info("bridge listening on http://127.0.0.1:8765")
    server.serve_forever()


if __name__ == "__main__":
    main()
