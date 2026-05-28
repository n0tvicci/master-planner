import json
from unittest.mock import MagicMock, patch
from backend.features.yt_shorts.services.script import generate_script

_MOCK_SCRIPT_RESPONSE = {
    "sentences": [
        {
            "text": "Most people think snipers always aim for the chest.",
            "pexels_query": "sniper rifle scope",
            "pixabay_query": "military sniper",
            "ai_needed": False,
            "ai_prompt": None,
            "keyword_overlay": "SNIPERS",
        },
        {
            "text": "It makes sense — Hollywood reinforces this every time.",
            "pexels_query": "movie action scene",
            "pixabay_query": "action film",
            "ai_needed": False,
            "ai_prompt": None,
            "keyword_overlay": "HOLLYWOOD",
        },
        {
            "text": "But real military snipers are trained to target the medulla oblongata.",
            "pexels_query": "military sniper training",
            "pixabay_query": "sniper training",
            "ai_needed": False,
            "ai_prompt": None,
            "keyword_overlay": "MEDULLA",
        },
        {
            "text": "Because it causes instant neurological shutdown — no muscle spasm, no trigger pull.",
            "pexels_query": "brain anatomy diagram",
            "pixabay_query": "neurology diagram",
            "ai_needed": True,
            "ai_prompt": "Close-up animation of brain stem being targeted",
            "keyword_overlay": "INSTANT STOP",
        },
    ],
    "originality_score": 8,
    "advertiser_friendliness_score": 9,
    "us_resonance_score": 8,
    "music_mood": "tense, suspenseful",
    "compliance": {
        "sensitive_content": "CLEAR",
        "sensitive_content_details": None,
        "ai_disclosure_required": True,
        "revision_notes": None,
    },
}


def _mock_anthropic(mock_class: MagicMock, response_json: dict) -> None:
    mock_client = MagicMock()
    mock_class.return_value = mock_client
    mock_client.messages.create.return_value.content[0].text = json.dumps(response_json)


def test_generate_script_returns_script_and_compliance():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        script, compliance_dict = generate_script(
            api_key="fake-key",
            topic_title="Why snipers never aim for the chest",
            misconception="Movies show center-mass shots",
        )
    assert len(script.sentences) == 4
    assert script.originality_score == 8
    assert script.status == "draft"
    assert isinstance(compliance_dict, dict)


def test_generate_script_computes_full_text():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        script, _ = generate_script("fake-key", "Title", "Misconception")
    expected = " ".join(s["text"] for s in _MOCK_SCRIPT_RESPONSE["sentences"])
    assert script.full_text == expected


def test_generate_script_assigns_sentence_ids():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        script, _ = generate_script("fake-key", "Title", "Misconception")
    ids = [s.id for s in script.sentences]
    assert len(set(ids)) == 4


def test_generate_script_uses_api_key():
    with patch("backend.features.yt_shorts.services.script.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_SCRIPT_RESPONSE)
        generate_script("my-real-key", "Title", "Misconception")
    MockClass.assert_called_once_with(api_key="my-real-key")
