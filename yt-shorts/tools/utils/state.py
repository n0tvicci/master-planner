import json
from pathlib import Path


def load_state(job_id: str, project_root: Path) -> dict:
    state_file = project_root / ".tmp" / job_id / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {"job_id": job_id, "completed_steps": []}


def save_state(state: dict, project_root: Path) -> None:
    state_file = project_root / ".tmp" / state["job_id"] / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps(state, indent=2))


def is_complete(step: str, state: dict) -> bool:
    return step in state.get("completed_steps", [])


def mark_complete(step: str, state: dict, project_root: Path) -> dict:
    state.setdefault("completed_steps", []).append(step)
    save_state(state, project_root)
    return state
