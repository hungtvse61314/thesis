from pydantic import BaseModel, Field
from typing import Literal


class RequirementIn(BaseModel):
    text: str = Field(min_length=1)
    kind: Literal["hard", "soft"] = "hard"
    category: Literal[
        "skill",
        "experience",
        "seniority",
        "responsibility",
        "education",
        "certification",
        "other",
    ] = "skill"
    weight: float = 1.0


class JDCreate(BaseModel):
    title: str = Field(min_length=2)
    description: str = Field(min_length=2)
    requirements: list[RequirementIn] = Field(default_factory=list)
    minimum_years: float = Field(default=0, ge=0)
    required_seniority: str = "unknown"


class LabelCreate(BaseModel):
    jd_id: int
    cv_id: int
    reviewer: str = "reviewer"
    label: int = Field(ge=0, le=3)
    note: str = ""
