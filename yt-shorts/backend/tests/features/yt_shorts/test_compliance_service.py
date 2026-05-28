from backend.features.yt_shorts.models.script import Script, ScriptSentence, ComplianceReport
from backend.features.yt_shorts.services.compliance import check_compliance

_SENTENCE = ScriptSentence(
    id="s1",
    text="Test sentence.",
    pexels_query="test",
    pixabay_query="test",
    ai_needed=False,
    keyword_overlay="TEST",
)


def _make_script(originality: int, advertiser: int) -> Script:
    return Script(
        sentences=[_SENTENCE],
        full_text="Test sentence.",
        originality_score=originality,
        advertiser_friendliness_score=advertiser,
        us_resonance_score=8,
        music_mood="tense",
    )


def test_compliance_passes_when_scores_meet_thresholds():
    script = _make_script(originality=7, advertiser=8)
    report = check_compliance(script)
    assert report.passed is True
    assert report.originality_status == "PASS"
    assert report.advertiser_status == "PASS"


def test_compliance_fails_when_originality_below_7():
    script = _make_script(originality=6, advertiser=9)
    report = check_compliance(script)
    assert report.passed is False
    assert report.originality_status == "REVISION_REQUIRED"
    assert report.advertiser_status == "PASS"


def test_compliance_fails_when_advertiser_below_8():
    script = _make_script(originality=8, advertiser=7)
    report = check_compliance(script)
    assert report.passed is False
    assert report.advertiser_status == "REVISION_REQUIRED"
    assert report.originality_status == "PASS"


def test_compliance_fails_when_both_below_threshold():
    script = _make_script(originality=5, advertiser=6)
    report = check_compliance(script)
    assert report.passed is False
    assert report.originality_status == "REVISION_REQUIRED"
    assert report.advertiser_status == "REVISION_REQUIRED"


def test_compliance_carries_scores():
    script = _make_script(originality=9, advertiser=9)
    report = check_compliance(script)
    assert report.originality_score == 9
    assert report.advertiser_friendliness_score == 9


def test_compliance_accepts_sensitive_content_from_claude():
    script = _make_script(originality=8, advertiser=8)
    report = check_compliance(
        script,
        sensitive_content="FLAG",
        sensitive_content_details="Mentions active conflict",
        revision_notes="Remove active conflict reference",
    )
    assert report.sensitive_content == "FLAG"
    assert report.sensitive_content_details == "Mentions active conflict"
    assert report.revision_notes == "Remove active conflict reference"


def test_compliance_ai_disclosure_always_true():
    script = _make_script(originality=8, advertiser=8)
    report = check_compliance(script)
    assert report.ai_disclosure_required is True
