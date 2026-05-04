from pydantic import BaseModel, Field

class AgeSuitability(BaseModel):
    suggested_rating: str
    rationale: str

class TagBundle(BaseModel):
    summary: str
    genres: list[str] = Field(default_factory=list)
    moods: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    objects: list[str] = Field(default_factory=list)
    settings: list[str] = Field(default_factory=list)
    content_warnings: list[str] = Field(default_factory=list)
    marketing_keywords: list[str] = Field(default_factory=list)
    search_keywords: list[str] = Field(default_factory=list)
    age_suitability: AgeSuitability
    confidence: float
