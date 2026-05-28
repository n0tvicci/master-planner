import json
import uuid
from pathlib import Path
from datetime import datetime, timezone


class ProjectStore:
    def __init__(self, base_dir: str = ".tmp/projects"):
        self.base = Path(base_dir)

    def _path(self, project_id: str) -> Path:
        return self.base / project_id / "state.json"

    def create(self, data: dict) -> dict:
        project_id = str(uuid.uuid4())
        project_dir = self.base / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        state = {**data, "id": project_id, "created_at": now, "updated_at": now}
        self._path(project_id).write_text(json.dumps(state))
        return state

    def get(self, project_id: str) -> dict | None:
        path = self._path(project_id)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def update(self, project_id: str, data: dict) -> dict:
        state = self.get(project_id)
        if state is None:
            raise ValueError(f"Project {project_id} not found")
        now = datetime.now(timezone.utc).isoformat()
        updated = {**state, **data, "updated_at": now}
        self._path(project_id).write_text(json.dumps(updated))
        return updated

    def list(self) -> list[dict]:
        if not self.base.exists():
            return []
        results = []
        for entry in self.base.iterdir():
            state_file = entry / "state.json"
            if entry.is_dir() and state_file.exists():
                results.append(json.loads(state_file.read_text()))
        return sorted(results, key=lambda x: x["created_at"], reverse=True)


def get_store() -> ProjectStore:
    return ProjectStore()
