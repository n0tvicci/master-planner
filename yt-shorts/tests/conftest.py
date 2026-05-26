import json
import os
import sys
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def project_root(tmp_path):
    for d in ["topics", ".tmp", "scripts", "voiceover", "footage", "assets",
              "music/tense", "music/dramatic", "music/suspenseful",
              "compliance-logs", "metadata", "output"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)

    saved_env = {}
    for key in ("PIPELINE_PROJECT_ROOT", "PUBLISH_PROJECT_ROOT"):
        saved_env[key] = os.environ.get(key)
        os.environ[key] = str(tmp_path)

    root_str = str(Path(__file__).parent.parent)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    active_patches = []
    for module_name in ("pipeline", "publish"):
        try:
            mod = __import__(module_name)
            p = patch.object(mod, "PROJECT_ROOT", tmp_path)
            p.start()
            active_patches.append(p)
        except (ImportError, AttributeError):
            pass

    yield tmp_path

    for p in active_patches:
        p.stop()
    for key, val in saved_env.items():
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


@pytest.fixture
def config():
    return {
        "anthropic_api_key": "test-key",
        "elevenlabs_api_key": "test-key",
        "elevenlabs_voice_id": "test-voice-id",
        "pexels_api_key": "test-key",
        "pixabay_api_key": "test-key",
        "runwayml_api_secret": "test-key",
    }


@pytest.fixture
def sample_topic():
    return {
        "id": "abc123",
        "title": "Why do real snipers never use laser sights in combat?",
        "misconception": "Laser sights give snipers a tactical advantage",
        "real_answer": "Lasers are visible to night vision, revealing your position",
        "us_score": 9,
        "status": "approved",
        "created_at": "2026-05-24T10:00:00Z",
    }


@pytest.fixture
def sample_script(project_root, sample_topic):
    script = {
        "job_id": "20260524-test-job",
        "topic": sample_topic,
        "word_count": 178,
        "estimated_duration_sec": 58,
        "tier_score": 9,
        "sentences": [
            {
                "index": 0,
                "text": "You've seen them in every action movie.",
                "section": "hook",
                "pexels_query": "laser sight rifle",
                "pixabay_query": "sniper rifle military",
                "needs_prop_library": True,
                "prop_description": "Rifle scope on dark surface, close-up glide shot",
                "needs_ai_video": False,
                "runway_prompt": None,
                "overlay": "EVERY MOVIE",
                "color_pop_words": ["EVERY"],
                "timestamp_approx": "0:00",
            },
            {
                "index": 1,
                "text": "But real snipers never use them in combat.",
                "section": "truth",
                "pexels_query": "military sniper rifle",
                "pixabay_query": "sniper combat",
                "needs_prop_library": False,
                "prop_description": None,
                "needs_ai_video": False,
                "runway_prompt": None,
                "overlay": "REAL SNIPERS",
                "color_pop_words": ["NEVER"],
                "timestamp_approx": "0:04",
            },
        ],
        "music_timing": {
            "dip_at_sentence_index": 1,
            "dip_timestamp_approx": "0:04",
            "dip_instruction": "Reduce music mid-range EQ or lower to -22dB",
            "swell_at_sentence_index": 1,
            "swell_timestamp_approx": "0:04",
            "swell_instruction": "Restore music to -16dB for final twist impact",
        },
        "loop": {
            "opening_shot_description": "Close-up glide across rifle scope on dark desk mat",
            "closing_shot_description": "Pull-back from scope to match exact opening frame",
            "loop_match_confirmed": True,
        },
        "background_music_mood": "Cinematic suspense, low-frequency atmospheric drone",
        "scores": {
            "originality": 8,
            "originality_breakdown": {
                "corrects_misconception": 2,
                "specific_historical_fact": 2,
                "non_obvious_mechanism": 2,
                "ironic_consequence_twist": 2,
                "beyond_footage_info": 0,
            },
            "advertiser_friendliness": 9,
            "advertiser_flags": [],
            "us_resonance": 9,
            "compliance_status": "PASS",
        },
        "compliance": {
            "originality": "PASS",
            "advertiser_friendliness": "PASS",
            "sensitive_content": "CLEAR",
            "ai_disclosure_required": "YES",
            "revision_notes": None,
        },
        "music_mood": "tense",
    }
    script_dir = project_root / "scripts" / "20260524-test-job"
    script_dir.mkdir(parents=True)
    (script_dir / "script.json").write_text(json.dumps(script))
    return script


@pytest.fixture
def sample_metadata():
    return {
        "title": "Why real snipers never use laser sights",
        "description": (
            "Laser sights reveal your position to enemy night vision. "
            "Real military snipers rely on scope magnification and iron sights. "
            "The laser sight is a Hollywood invention — deadly in movies, fatal in combat. "
            "Follow for more military history myths debunked."
        ),
        "tags": [
            "military history", "snipers", "weapons facts", "laser sights",
            "combat tactics", "did you know", "military myths", "special forces",
            "rifle", "historical weapons",
        ],
        "pinned_comment": "Would you risk it with a laser sight in real combat? Drop your answer below.",
    }
