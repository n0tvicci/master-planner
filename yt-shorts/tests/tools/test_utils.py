import json
import pytest
from pathlib import Path
from tools.utils.state import load_state, save_state, is_complete, mark_complete
from tools.utils.job import make_job_id


def test_make_job_id_format():
    job_id = make_job_id("Why do real snipers never use laser sights?")
    assert job_id[:8].isdigit()  # YYYYMMDD prefix
    assert "-" in job_id
    assert job_id == job_id.lower()


def test_make_job_id_slug_truncated():
    job_id = make_job_id("Why do real snipers never use laser sights in combat today?")
    parts = job_id.split("-")
    # date part (8 digits) + max 5 slug words
    assert len(parts) <= 6


def test_load_state_missing_returns_empty(tmp_path):
    state = load_state("nonexistent-job", tmp_path)
    assert state["job_id"] == "nonexistent-job"
    assert state["completed_steps"] == []


def test_save_and_load_state(tmp_path):
    state = {"job_id": "test-job", "completed_steps": ["generate_script"]}
    save_state(state, tmp_path)
    loaded = load_state("test-job", tmp_path)
    assert loaded["completed_steps"] == ["generate_script"]


def test_is_complete(tmp_path):
    state = {"job_id": "j", "completed_steps": ["generate_script"]}
    assert is_complete("generate_script", state) is True
    assert is_complete("generate_voiceover", state) is False


def test_mark_complete_saves_and_returns(tmp_path):
    state = {"job_id": "j", "completed_steps": []}
    state = mark_complete("generate_script", state, tmp_path)
    assert "generate_script" in state["completed_steps"]
    loaded = load_state("j", tmp_path)
    assert "generate_script" in loaded["completed_steps"]
