import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parent.parent
CAPTURE_ROOT = REPO_ROOT / "docs" / "overwolf-testdata" / "raw-payloads"
CAPTURE_KIND_BY_PATH = {
    "/capture/set-required-features": "set_required_features",
    "/capture/running-game-info": "running_game_info",
    "/capture/info-updates": "info_updates",
    "/capture/new-events": "new_events",
}


class CaptureSession:
    def __init__(self) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.session_dir = CAPTURE_ROOT / f"{timestamp}_manual-run"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.files = {
            "set_required_features": self.session_dir / "set-required-features.json",
            "running_game_info": self.session_dir / "running-game-info.json",
            "info_updates": self.session_dir / "info-updates.json",
            "new_events": self.session_dir / "new-events.json",
        }
        self.payloads: Dict[str, List[Dict[str, Any]]] = {
            "set_required_features": [],
            "running_game_info": [],
            "info_updates": [],
            "new_events": [],
        }
        self._ensure_notes_file()
        self._flush_all()

    def append(self, kind: str, payload: Dict[str, Any]) -> None:
        if kind not in self.payloads:
            raise KeyError(f"unknown capture kind: {kind}")

        entry = {
            "capturedAt": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        self.payloads[kind].append(entry)
        self.files[kind].write_text(
            json.dumps(self.payloads[kind], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def status(self) -> Dict[str, Any]:
        return {
            "session_dir": str(self.session_dir),
            "counts": {
                "set_required_features": len(self.payloads["set_required_features"]),
                "running_game_info": len(self.payloads["running_game_info"]),
                "info_updates": len(self.payloads["info_updates"]),
                "new_events": len(self.payloads["new_events"]),
            },
        }

    def _ensure_notes_file(self) -> None:
        template_path = REPO_ROOT / "docs" / "overwolf-testdata" / "capture-log-template.md"
        notes_path = self.session_dir / "notes.md"
        if template_path.exists():
            notes_path.write_text(template_path.read_text(encoding="utf-8"), encoding="utf-8")
            return

        notes_path.write_text("# Capture Session\n", encoding="utf-8")

    def _flush_all(self) -> None:
        for kind, path in self.files.items():
            path.write_text(
                json.dumps(self.payloads[kind], ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


CAPTURE_SESSION = CaptureSession()
