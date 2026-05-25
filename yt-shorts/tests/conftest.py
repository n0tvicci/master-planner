import json
import pytest
from pathlib import Path


@pytest.fixture
def project_root(tmp_path):
    for d in ["topics", ".tmp", "scripts", "voiceover", "footage", "assets",
              "music/tense", "music/dramatic", "music/suspenseful",
              "compliance-logs", "metadata", "output"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def config():
    return {
        "anthropic_api_key": "test-key",
        "elevenlabs_api_key": "test-key",
        "elevenlabs_voice_id": "test-voice-id",
        "pexels_api_key": "test-key",
        "pixabay_api_key": "test-key",
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
