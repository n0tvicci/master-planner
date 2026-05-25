"""
generate_voiceover.py — Generate voiceover via ElevenLabs REST API.

Usage:
    python tools/generate_voiceover.py <job_id> [voice_id]

Args:
    job_id      — Unique job identifier (e.g. 20260524-abc123)
    voice_id    — Optional ElevenLabs voice ID override (defaults to env ELEVENLABS_VOICE_ID)

Outputs:
    voiceover/<job_id>/voiceover.mp3 — Audio file
"""

import json
from pathlib import Path
import requests


def run(
    job_id: str,
    config: dict,
    project_root: Path,
    voice_id: str | None = None,
) -> Path:
    """
    Generate voiceover from script sentences via ElevenLabs TTS.

    Args:
        job_id: Unique job identifier
        config: Dict with keys: elevenlabs_api_key, elevenlabs_voice_id
        project_root: Project root path
        voice_id: Optional voice ID override

    Returns:
        Path to generated MP3 file
    """
    script = json.loads((project_root / "scripts" / job_id / "script.json").read_text())
    full_text = " ".join(s["text"] for s in script["sentences"])

    vid = voice_id or config["elevenlabs_voice_id"]
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"

    response = requests.post(
        url,
        headers={
            "xi-api-key": config["elevenlabs_api_key"],
            "Content-Type": "application/json",
        },
        json={
            "text": full_text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.70,
                "similarity_boost": 0.82,
                "style": 0.37,
                "use_speaker_boost": True,
            },
        },
    )
    response.raise_for_status()

    out_dir = project_root / "voiceover" / job_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "voiceover.mp3"
    out_path.write_bytes(response.content)
    print(f"✓ Voiceover saved: {out_path}")
    return out_path


if __name__ == "__main__":
    import sys
    from tools.utils.config import load_config
    project_root = Path(__file__).parent.parent
    job_id = sys.argv[1]
    voice_id = sys.argv[2] if len(sys.argv) > 2 else None
    run(job_id, load_config(), project_root, voice_id)
