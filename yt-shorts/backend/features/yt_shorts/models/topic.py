from pydantic import BaseModel, ConfigDict
from typing import Literal


class Topic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    misconception: str
    real_answer: str
    us_curiosity_score: int
    status: Literal["pending", "approved"] = "pending"
