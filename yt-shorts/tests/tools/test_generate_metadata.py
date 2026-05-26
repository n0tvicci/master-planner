import json
import pytest
from unittest.mock import MagicMock, patch
import tools.generate_metadata as generate_metadata


def test_run_calls_claude_and_saves_metadata(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({
        "title": "Why snipers never use lasers",
        "description": "Laser sights reveal your position. Military snipers avoid them.",
        "tags": ["military", "snipers", "weapons facts"],
        "pinned_comment": "Would you use a laser in combat?",
    }))]

    with patch("tools.generate_metadata.anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_response
        result = generate_metadata.run("20260524-test-job", config, project_root)

    assert result["title"] == "Why snipers never use lasers"
    metadata_path = project_root / "metadata" / "20260524-test-job" / "metadata.json"
    assert metadata_path.exists()
    saved = json.loads(metadata_path.read_text())
    assert saved["title"] == "Why snipers never use lasers"


def test_run_raises_if_script_missing(project_root, config):
    with pytest.raises(FileNotFoundError, match="script.json"):
        generate_metadata.run("no-such-job", config, project_root)


def test_run_raises_on_non_json_claude_response(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Sorry, I cannot help with that.")]

    with patch("tools.generate_metadata.anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_response
        with pytest.raises(RuntimeError, match="non-JSON"):
            generate_metadata.run("20260524-test-job", config, project_root)


def test_run_raises_on_empty_claude_response(project_root, config, sample_script):
    mock_response = MagicMock()
    mock_response.content = []

    with patch("tools.generate_metadata.anthropic.Anthropic") as mock_client_cls:
        mock_client_cls.return_value.messages.create.return_value = mock_response
        with pytest.raises(RuntimeError, match="empty response"):
            generate_metadata.run("20260524-test-job", config, project_root)
