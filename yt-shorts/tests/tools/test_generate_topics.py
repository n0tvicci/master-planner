import json
import pytest
from unittest.mock import MagicMock, patch
from tools.generate_topics import run, append_to_queue


def make_mock_response(topics_json: str):
    mock = MagicMock()
    mock.content = [MagicMock(text=topics_json)]
    return mock


SAMPLE_TOPICS_JSON = json.dumps([
    {
        "title": "Why do real snipers never use laser sights in combat?",
        "misconception": "Laser sights give a tactical advantage",
        "real_answer": "Lasers reveal your position to night vision",
        "us_score": 9,
        "tier": 1,
    },
    {
        "title": "Why did the US Army abandon the M14 rifle so quickly?",
        "misconception": "The M14 was a failed design",
        "real_answer": "It was accurate but wrong for jungle warfare",
        "us_score": 8,
        "tier": 1,
    },
])


def test_run_calls_claude_api(config):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_TOPICS_JSON)

        topics = run(config)

    assert len(topics) == 2
    assert topics[0]["title"].startswith("Why")
    assert "us_score" in topics[0]
    mock_client.messages.create.assert_called_once()


def test_run_passes_cache_control(config):
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_TOPICS_JSON)

        run(config)

    call_kwargs = mock_client.messages.create.call_args[1]
    system = call_kwargs["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_append_to_queue_creates_file(project_root):
    topics = [{"title": "Test", "misconception": "X", "real_answer": "Y", "us_score": 7}]
    append_to_queue(topics, project_root)

    queue_file = project_root / "topics" / "queue.json"
    assert queue_file.exists()
    queue = json.loads(queue_file.read_text())
    assert len(queue) == 1
    assert queue[0]["status"] == "pending"
    assert "id" in queue[0]
    assert "created_at" in queue[0]


def test_append_to_queue_merges_with_existing(project_root):
    existing = [{"id": "old1", "title": "Old Topic", "status": "used"}]
    (project_root / "topics" / "queue.json").write_text(json.dumps(existing))

    topics = [{"title": "New Topic", "misconception": "X", "real_answer": "Y", "us_score": 8}]
    append_to_queue(topics, project_root)

    queue = json.loads((project_root / "topics" / "queue.json").read_text())
    assert len(queue) == 2
    assert queue[0]["id"] == "old1"
    assert queue[1]["title"] == "New Topic"


def test_run_injects_published_titles_into_prompt(project_root, config):
    (project_root / "topics").mkdir(parents=True, exist_ok=True)
    (project_root / "topics" / "published.json").write_text(json.dumps([
        {"title": "Why do snipers avoid laser sights?", "job_id": "old-job-1"},
    ]))
    with patch("anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = make_mock_response(SAMPLE_TOPICS_JSON)

        run(config, project_root)

    call_kwargs = mock_client.messages.create.call_args[1]
    user_msg = call_kwargs["messages"][0]["content"]
    assert "snipers avoid laser sights" in user_msg
    assert "AVOID" in user_msg
