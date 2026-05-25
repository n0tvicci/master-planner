"""
select_music.py — Select mood-appropriate background music from local library.

Usage:
    python tools/select_music.py <job_id>

Args:
    job_id      — Unique job identifier (e.g. 20260524-abc123)

Outputs:
    assets/<job_id>/music.mp3 — Selected music track
"""

import json
import random
import shutil
from pathlib import Path

MOOD_FOLDERS = {
    "tense": ["tense", "suspenseful"],
    "dramatic": ["dramatic"],
    "suspenseful": ["tense", "suspenseful"],
}


def run(job_id: str, project_root: Path) -> Path:
    """
    Select and copy mood-appropriate music track to asset bundle.

    Args:
        job_id: Unique job identifier
        project_root: Project root path

    Returns:
        Path to copied music.mp3 file in assets/<job_id>/

    Raises:
        FileNotFoundError: If script not found or no music tracks available
        RuntimeError: If script cannot be read
    """
    script_file = project_root / "scripts" / job_id / "script.json"
    if not script_file.exists():
        raise FileNotFoundError(f"Script not found: {script_file}. Run generate_script first.")
    try:
        script = json.loads(script_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"Could not read script for job {job_id}: {e}") from e

    mood = script.get("music_mood", "tense")

    music_root = project_root / "music"
    candidates = []
    for folder_name in MOOD_FOLDERS.get(mood, [mood]):
        folder = music_root / folder_name
        if folder.exists():
            candidates.extend(folder.glob("*.mp3"))

    if not candidates:
        candidates = list(music_root.glob("**/*.mp3"))

    if not candidates:
        raise FileNotFoundError(
            f"No music tracks found in {music_root}. "
            "Add royalty-free MP3s to music/tense/, music/dramatic/, or music/suspenseful/."
        )

    chosen = random.choice(candidates)
    out_dir = project_root / "assets" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "music.mp3"
    shutil.copy2(chosen, out_path)
    print(f"✅ Music selected: {chosen.name} (mood: {mood})")
    return out_path


if __name__ == "__main__":
    import sys
    project_root = Path(__file__).parent.parent
    run(sys.argv[1], project_root)
