import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def strip_audio(input_path: Path, output_path: Path) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-i", str(input_path), "-an", "-c:v", "copy", "-y", str(output_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def run(job_id: str, project_root: Path) -> dict:
    footage_dir = project_root / "footage" / job_id
    clips = sorted(footage_dir.glob("clip_*.mp4"))

    log = {
        "job_id": job_id,
        "cleared_at": datetime.now(timezone.utc).isoformat(),
        "clips": [],
    }
    failed = []

    for clip in clips:
        tmp = clip.with_suffix(".noaudio.mp4")
        if strip_audio(clip, tmp):
            tmp.replace(clip)
            log["clips"].append({"file": clip.name, "status": "cleared", "audio_stripped": True})
            print(f"  ✅ {clip.name} — audio stripped")
        else:
            failed.append(clip.name)
            log["clips"].append({"file": clip.name, "status": "failed"})
            print(f"  ❌ {clip.name} — ffmpeg failed")

    log_dir = project_root / "compliance-logs" / job_id
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "clearance.json").write_text(json.dumps(log, indent=2))

    if failed:
        raise RuntimeError(f"Audio stripping failed for: {', '.join(failed)}")

    print(f"✅ {len(clips)} clips cleared")
    return log


if __name__ == "__main__":
    import sys
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], project_root)
