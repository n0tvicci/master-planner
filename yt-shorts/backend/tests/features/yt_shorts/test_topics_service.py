import json
from unittest.mock import MagicMock, patch
from backend.features.yt_shorts.services.topics import generate_topics

_MOCK_TOPICS = {
    "topics": [
        {
            "title": f"Why do real snipers never target the chest — {i}",
            "misconception": "Movies show center-mass shots",
            "real_answer": "CNS targeting for instant incapacitation",
            "us_curiosity_score": 10 - i,
        }
        for i in range(10)
    ]
}


def _mock_anthropic(mock_class: MagicMock, response_json: dict) -> MagicMock:
    mock_client = MagicMock()
    mock_class.return_value = mock_client
    mock_client.messages.create.return_value.content[0].text = json.dumps(response_json)
    return mock_client


def test_generate_topics_returns_ten():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_TOPICS)
        topics = generate_topics("fake-key")
        assert len(topics) == 10


def test_generate_topics_assigns_unique_ids():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_TOPICS)
        topics = generate_topics("fake-key")
        ids = [t.id for t in topics]
        assert len(set(ids)) == 10


def test_generate_topics_status_is_pending():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        _mock_anthropic(MockClass, _MOCK_TOPICS)
        topics = generate_topics("fake-key")
        assert all(t.status == "pending" for t in topics)


def test_generate_topics_uses_api_key():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        mock_client = _mock_anthropic(MockClass, _MOCK_TOPICS)
        generate_topics("my-real-key")
        MockClass.assert_called_once_with(api_key="my-real-key")


def test_generate_topics_raises_on_invalid_json():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        mock_client.messages.create.return_value.content[0].text = "not valid json"
        import pytest
        with pytest.raises(ValueError, match="Invalid JSON"):
            generate_topics("fake-key")


def test_generate_topics_raises_on_wrong_count():
    with patch("backend.features.yt_shorts.services.topics.Anthropic") as MockClass:
        mock_client = MagicMock()
        MockClass.return_value = mock_client
        only_five = {"topics": [{"title": f"T{i}", "misconception": "X", "real_answer": "Y", "us_curiosity_score": 5} for i in range(5)]}
        mock_client.messages.create.return_value.content[0].text = json.dumps(only_five)
        import pytest
        with pytest.raises(ValueError, match="Expected 10 topics"):
            generate_topics("fake-key")
