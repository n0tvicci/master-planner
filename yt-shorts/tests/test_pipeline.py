import json
import sys
import pytest
from unittest.mock import MagicMock, patch, call
from pathlib import Path


def write_approved_queue(project_root, topic):
    queue = [topic]
    (project_root / "topics" / "queue.json").write_text(json.dumps(queue))


def write_state(project_root, job_id, completed_steps):
    state = {"job_id": job_id, "topic": {}, "topic_id": "x", "completed_steps": completed_steps}
    (project_root / ".tmp" / job_id).mkdir(parents=True, exist_ok=True)
    (project_root / ".tmp" / job_id / "state.json").write_text(json.dumps(state))


def test_topics_only_flag_calls_generate_and_exits(project_root, config, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--topics-only"])
    monkeypatch.setattr("sys.path", [str(project_root)] + sys.path)

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_topics.run", return_value=[]) as mock_gen, \
         patch("tools.generate_topics.append_to_queue") as mock_append:
        import importlib
        import pipeline
        importlib.reload(pipeline)
        pipeline.main()

    mock_gen.assert_called_once()
    mock_append.assert_called_once()


def test_exits_cleanly_when_no_approved_topic(project_root, config, monkeypatch, capsys):
    (project_root / "topics" / "queue.json").write_text("[]")
    monkeypatch.setattr("sys.argv", ["pipeline.py"])

    with patch("tools.utils.config.load_config", return_value=config):
        import pipeline
        with pytest.raises(SystemExit) as exc:
            pipeline.main()
        assert exc.value.code == 0

    captured = capsys.readouterr()
    assert "No approved topics" in captured.out


def test_full_run_calls_all_steps_in_order(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py"])

    call_order = []

    def track(name):
        def fn(*a, **kw):
            call_order.append(name)
            return MagicMock()
        return fn

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", side_effect=track("generate_script")), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}, side_effect=lambda *a, **kw: call_order.append("check_compliance") or {"status": "PASS"}), \
         patch("tools.generate_voiceover.run", side_effect=track("generate_voiceover")), \
         patch("tools.select_music.run", side_effect=track("select_music")), \
         patch("tools.search_footage.run", side_effect=track("search_footage")), \
         patch("tools.clear_footage.run", side_effect=track("clear_footage")), \
         patch("tools.check_footage_gaps.run", side_effect=lambda *a, **kw: call_order.append("check_footage_gaps") or {"ai_gaps": [], "prop_library_gaps": []}), \
         patch("tools.generate_ai_footage.run", side_effect=track("generate_ai_footage")), \
         patch("tools.package_assets.run", side_effect=track("package_assets")):
        import pipeline
        pipeline.main()

    assert call_order == [
        "generate_script", "check_compliance", "generate_voiceover",
        "select_music", "search_footage", "clear_footage",
        "check_footage_gaps", "generate_ai_footage", "package_assets",
    ]


def test_revise_flag_clears_script_steps(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--revise"])

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": []}), \
         patch("tools.generate_ai_footage.run", return_value=[]), \
         patch("tools.package_assets.run", return_value=MagicMock()):
        import pipeline
        pipeline.main()  # should not raise


def test_approve_topics_flag_updates_queue_interactively(project_root, config, monkeypatch):
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--approve-topics"])
    queue = [
        {"id": "t1", "title": "Why do snipers avoid lasers?", "tier": 1, "tier_score": 9, "status": "pending"},
        {"id": "t2", "title": "Why did the M14 fail?", "tier": 2, "tier_score": 7, "status": "pending"},
    ]
    (project_root / "topics" / "queue.json").write_text(json.dumps(queue))

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("builtins.input", side_effect=["y", "n"]):
        import importlib
        import pipeline
        importlib.reload(pipeline)
        pipeline.main()

    updated = json.loads((project_root / "topics" / "queue.json").read_text())
    assert updated[0]["status"] == "approved"
    assert updated[1]["status"] == "pending"


def test_compliance_auto_retries_on_failure(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py"])
    script_dir = project_root / "scripts" / "20260524-why-do-real-snipers"
    script_dir.mkdir(parents=True, exist_ok=True)
    (script_dir / "script.json").write_text(json.dumps({"compliance": {"revision_notes": "fix it"}}))

    compliance_results = [
        {"status": "REVISION_REQUIRED", "notes": "originality too low"},
        {"status": "PASS"},
    ]

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}) as mock_script, \
         patch("tools.check_compliance.run", side_effect=compliance_results), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": []}), \
         patch("tools.generate_ai_footage.run", return_value=[]), \
         patch("tools.package_assets.run", return_value=MagicMock()):
        import pipeline
        pipeline.main()

    # generate_script called twice: initial + 1 auto-retry
    assert mock_script.call_count == 2


def test_prop_gaps_attempt_runway_fallback_by_default(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py"])

    prop_gap = [{"sentence_idx": 0, "runway_prompt": "desk prop", "needs_prop_library": True}]

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": prop_gap}), \
         patch("tools.generate_ai_footage.run", return_value=[{"status": "generated"}]) as mock_runway, \
         patch("tools.package_assets.run", return_value=MagicMock()):
        import pipeline
        pipeline.main()

    mock_runway.assert_called()


def test_prop_gaps_halt_with_strict_props_flag(project_root, config, sample_topic, monkeypatch):
    write_approved_queue(project_root, sample_topic)
    monkeypatch.setattr("sys.argv", ["pipeline.py", "--strict-props"])

    prop_gap = [{"sentence_idx": 0, "runway_prompt": "desk prop", "needs_prop_library": True}]

    with patch("tools.utils.config.load_config", return_value=config), \
         patch("tools.generate_script.run", return_value={"sentences": []}), \
         patch("tools.check_compliance.run", return_value={"status": "PASS"}), \
         patch("tools.generate_voiceover.run", return_value=MagicMock()), \
         patch("tools.select_music.run", return_value=MagicMock()), \
         patch("tools.search_footage.run", return_value=[]), \
         patch("tools.clear_footage.run", return_value={}), \
         patch("tools.check_footage_gaps.run", return_value={"ai_gaps": [], "prop_library_gaps": prop_gap}), \
         patch("tools.generate_ai_footage.run", return_value=[]) as mock_runway, \
         patch("tools.package_assets.run", return_value=MagicMock()):
        with pytest.raises(SystemExit) as exc:
            import pipeline
            pipeline.main()
        assert exc.value.code == 0  # clean pause, not error

    mock_runway.assert_not_called()  # Runway not attempted with --strict-props
