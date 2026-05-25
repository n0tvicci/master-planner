import json
import pytest
from tools.check_compliance import run


def write_script(project_root, job_id, originality, advertiser, sensitive="CLEAR", revision_notes=None):
    script = {
        "job_id": job_id,
        "scores": {"originality": originality, "advertiser_friendliness": advertiser, "us_resonance": 8},
        "compliance": {
            "originality": "PASS" if originality >= 7 else "REVISION REQUIRED",
            "advertiser_friendliness": "PASS" if advertiser >= 8 else "REVISION REQUIRED",
            "sensitive_content": sensitive,
            "ai_disclosure_required": "YES",
            "revision_notes": revision_notes,
        },
    }
    d = project_root / "scripts" / job_id
    d.mkdir(parents=True)
    (d / "script.json").write_text(json.dumps(script))


def test_pass_when_scores_meet_minimums(project_root):
    write_script(project_root, "job-pass", originality=8, advertiser=9)
    result = run("job-pass", project_root)
    assert result["status"] == "PASS"


def test_fail_when_originality_below_7(project_root):
    write_script(project_root, "job-orig", originality=6, advertiser=9,
                 revision_notes="Add a specific historical event.")
    result = run("job-orig", project_root)
    assert result["status"] == "REVISION_REQUIRED"
    assert result["notes"] == "Add a specific historical event."


def test_fail_when_advertiser_below_8(project_root):
    write_script(project_root, "job-adv", originality=8, advertiser=7,
                 revision_notes="Remove the reference to combat casualties.")
    result = run("job-adv", project_root)
    assert result["status"] == "REVISION_REQUIRED"


def test_fail_when_sensitive_content_flagged(project_root):
    write_script(project_root, "job-sens", originality=8, advertiser=9,
                 sensitive="FLAG", revision_notes="Script references active conflict.")
    result = run("job-sens", project_root)
    assert result["status"] == "REVISION_REQUIRED"
