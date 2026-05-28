from typing import Literal, Optional
from backend.features.yt_shorts.models.script import Script, ComplianceReport

_ORIGINALITY_MIN = 7
_ADVERTISER_MIN = 8


def check_compliance(
    script: Script,
    sensitive_content: Literal["CLEAR", "FLAG"] = "CLEAR",
    sensitive_content_details: Optional[str] = None,
    revision_notes: Optional[str] = None,
) -> ComplianceReport:
    originality_ok = script.originality_score >= _ORIGINALITY_MIN
    advertiser_ok = script.advertiser_friendliness_score >= _ADVERTISER_MIN
    return ComplianceReport(
        originality_score=script.originality_score,
        advertiser_friendliness_score=script.advertiser_friendliness_score,
        originality_status="PASS" if originality_ok else "REVISION_REQUIRED",
        advertiser_status="PASS" if advertiser_ok else "REVISION_REQUIRED",
        sensitive_content=sensitive_content,
        sensitive_content_details=sensitive_content_details,
        ai_disclosure_required=True,
        passed=originality_ok and advertiser_ok,
        revision_notes=revision_notes,
    )
