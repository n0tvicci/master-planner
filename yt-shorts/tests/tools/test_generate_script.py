import json
import pytest
from unittest.mock import MagicMock, patch
from tools.generate_script import run


def make_mock_response(script_dict: dict):
    mock = MagicMock()
    mock.content = [MagicMock(text=json.dumps(script_dict))]
    return mock


SAMPLE_SCRIPT_RESPONSE = {
    "status": "PASS",
    "word_count": 178,
    "estimated_duration_sec": 58,
    "tier_score": 9,
    "sentences": [
        {
            "index": 0,
            "text": "You've seen them in every action movie.",
            "section": "hook",
            "timestamp_approx": "0:00",
            "pexels_query": "laser sight rifle",
            "pixabay_query": "sniper rifle military",
            "needs_prop_library": True,
            "prop_description": "Rifle scope on dark surface, close-up glide",
            "needs_ai_video": False,
            "runway_prompt": None,
            "overlay": "EVERY MOVIE",
            "color_pop_words": ["EVERY"],
        }
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


def test_run_creates_script_json(project_root, config, sample_topic):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_SCRIPT_RESPONSE)

        result = run("20260524-test-job", sample_topic, config, project_root)

    script_file = project_root / "scripts" / "20260524-test-job" / "script.json"
    assert script_file.exists()
    saved = json.loads(script_file.read_text())
    assert saved["job_id"] == "20260524-test-job"
    assert saved["topic"]["id"] == sample_topic["id"]
    assert len(saved["sentences"]) == 1


def test_run_returns_script_dict(project_root, config, sample_topic):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_SCRIPT_RESPONSE)

        result = run("20260524-test-job", sample_topic, config, project_root)

    assert result["job_id"] == "20260524-test-job"
    assert "sentences" in result
    assert "scores" in result


def test_run_with_revision_context_appends_to_message(project_root, config, sample_topic):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_SCRIPT_RESPONSE)

        run("20260524-test-job", sample_topic, config, project_root,
            revision_context="Originality too low — add a specific historical event.")

    call_kwargs = mock_client.messages.create.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "PREVIOUS REVISION REQUIRED" in user_content
    assert "historical event" in user_content


def test_run_auto_regenerates_when_word_count_out_of_range(project_root, config, sample_topic):
    # First response has 1-word sentence (way under 168) → triggers re-generation
    short_script = {
        **SAMPLE_SCRIPT_RESPONSE,
        "status": "PASS",
        "sentences": [
            {
                "index": 0, "text": "Short.", "section": "hook",
                "timestamp_approx": "0:00", "pexels_query": "x", "pixabay_query": "x",
                "needs_prop_library": False, "prop_description": None,
                "needs_ai_video": False, "runway_prompt": None,
                "overlay": "SHORT", "color_pop_words": [],
            }
        ],
    }
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.side_effect = [
            make_mock_response(short_script),
            make_mock_response(SAMPLE_SCRIPT_RESPONSE),
        ]
        run("20260524-test-job", sample_topic, config, project_root)

    assert mock_client.messages.create.call_count == 2
    # Second call includes the word count correction in the message history
    second_call = mock_client.messages.create.call_args_list[1][1]
    messages = second_call["messages"]
    assert any("WORD COUNT CORRECTION" in str(m) for m in messages)
