from backend.features.yt_shorts.models.script import (
    Script,
    ScriptSentence,
    ComplianceReport,
    ScriptResponse,
)


def _make_sentence(i: int = 0) -> ScriptSentence:
    return ScriptSentence(
        id=f"s{i}",
        text=f"Sentence {i} text here.",
        pexels_query=f"military weapon {i}",
        pixabay_query=f"army equipment {i}",
        ai_needed=False,
        keyword_overlay=f"WEAPON{i}",
    )


def test_script_sentence_defaults():
    s = _make_sentence(0)
    assert s.ai_needed is False
    assert s.ai_prompt is None


def test_script_defaults_to_draft():
    sentences = [_make_sentence(i) for i in range(4)]
    script = Script(
        sentences=sentences,
        full_text="Hook. Validation. Truth. Twist.",
        originality_score=8,
        advertiser_friendliness_score=9,
        us_resonance_score=8,
        music_mood="tense, dramatic",
    )
    assert script.status == "draft"


def test_script_serializes():
    sentences = [_make_sentence(0)]
    script = Script(
        sentences=sentences,
        full_text="Test sentence.",
        originality_score=8,
        advertiser_friendliness_score=9,
        us_resonance_score=7,
        music_mood="intense",
    )
    data = script.model_dump()
    assert data["status"] == "draft"
    assert data["originality_score"] == 8
    assert len(data["sentences"]) == 1


def test_compliance_report_passed_flag():
    report = ComplianceReport(
        originality_score=8,
        advertiser_friendliness_score=9,
        originality_status="PASS",
        advertiser_status="PASS",
        sensitive_content="CLEAR",
        ai_disclosure_required=True,
        passed=True,
    )
    assert report.passed is True
    assert report.sensitive_content_details is None


def test_script_response_wraps_both():
    sentences = [_make_sentence(0)]
    script = Script(
        sentences=sentences,
        full_text="Test.",
        originality_score=8,
        advertiser_friendliness_score=9,
        us_resonance_score=8,
        music_mood="dark",
    )
    report = ComplianceReport(
        originality_score=8,
        advertiser_friendliness_score=9,
        originality_status="PASS",
        advertiser_status="PASS",
        sensitive_content="CLEAR",
        ai_disclosure_required=True,
        passed=True,
    )
    resp = ScriptResponse(script=script, compliance=report)
    assert resp.script.status == "draft"
    assert resp.compliance.passed is True
