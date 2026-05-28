from pydantic import BaseModel, ConfigDict
from typing import Literal, Optional


class Voiceover(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audio_path: str
    duration_seconds: Optional[float] = None
    status: Literal["generated", "approved"] = "generated"
