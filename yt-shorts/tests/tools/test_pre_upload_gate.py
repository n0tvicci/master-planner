import pytest
from unittest.mock import patch
import tools.pre_upload_gate as pre_upload_gate


def test_all_yes_returns_pass():
    # All 5 checks "y", final confirm "YES"
    answers = ["y", "y", "y", "y", "y", "YES"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result == {"status": "PASS"}


def test_any_no_returns_fail_with_check_listed():
    # Third check fails
    answers = ["y", "y", "n", "y", "y"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
    assert any("54–60 sec" in c for c in result["failed_checks"])


def test_multiple_no_answers_all_listed():
    answers = ["n", "y", "n", "y", "y"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
    assert len(result["failed_checks"]) == 2


def test_final_no_returns_fail():
    # All checks pass but user types NO at final prompt
    answers = ["y", "y", "y", "y", "y", "NO"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
    assert result["failed_checks"] == ["Final confirmation not given"]


def test_final_lowercase_yes_returns_fail():
    # "yes" is not the same as "YES" — must be exact
    answers = ["y", "y", "y", "y", "y", "yes"]
    with patch("builtins.input", side_effect=answers):
        result = pre_upload_gate.run()
    assert result["status"] == "FAIL"
