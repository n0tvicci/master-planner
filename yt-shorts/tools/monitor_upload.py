from datetime import datetime, timezone
from pathlib import Path

from tools.utils.state import load_state, save_state


def run(job_id: str, video_id: str, title: str, project_root: Path) -> None:
    state = load_state(job_id, project_root)
    state["uploaded_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state, project_root)

    url = f"https://youtube.com/shorts/{video_id}"
    print(f"""
Uploaded: {title}
   Video ID: {video_id}
   URL: {url}

24h  -> Check for copyright claims
48h  -> Confirm monetization status is green
72h  -> Check country distribution (target: 50%+ US)
       Run: python publish.py --job {job_id} --analytics
""")
