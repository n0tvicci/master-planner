from enum import Enum
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ProjectStep(str, Enum):
    TOPICS = "topics"
    SCRIPT = "script"
    VOICEOVER = "voiceover"
    FOOTAGE_SEARCH = "footage_search"
    FOOTAGE_AI = "footage_ai"
    MUSIC = "music"
    ASSETS = "assets"
    GATE = "gate"
    METADATA = "metadata"
    PUBLISH = "publish"
    MONITOR = "monitor"
    COMPLETE = "complete"


class ProjectCreate(BaseModel):
    title: str


class Project(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    current_step: ProjectStep
    created_at: datetime
    updated_at: datetime
    # Step outputs — populated as project advances
    approved_topic: Optional[dict] = None
    script_draft: Optional[dict] = None
    compliance_report: Optional[dict] = None
    voiceover: Optional[dict] = None
    footage_clips: list[dict] = []
    ai_clips: list[dict] = []
    selected_track: Optional[dict] = None
    assets_path: Optional[str] = None
    gate_result: Optional[dict] = None
    metadata: Optional[dict] = None
    youtube_video_id: Optional[str] = None
