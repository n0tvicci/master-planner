from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional


class ScriptSentence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    text: str
    pexels_query: str
    pixabay_query: str
    ai_needed: bool
    ai_prompt: Optional[str] = None
    keyword_overlay: str


class Script(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sentences: list[ScriptSentence]
    full_text: str
    originality_score: int
    advertiser_friendliness_score: int
    us_resonance_score: int
    music_mood: str
    status: Literal["draft", "approved"] = "draft"


class ComplianceReport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    originality_score: int
    advertiser_friendliness_score: int
    originality_status: Literal["PASS", "REVISION_REQUIRED"]
    advertiser_status: Literal["PASS", "REVISION_REQUIRED"]
    sensitive_content: Literal["CLEAR", "FLAG"]
    sensitive_content_details: Optional[str] = None
    ai_disclosure_required: bool
    passed: bool
    revision_notes: Optional[str] = None


class ScriptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    script: Optional[Script] = None
    compliance: Optional[ComplianceReport] = None
