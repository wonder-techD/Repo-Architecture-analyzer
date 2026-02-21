from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")


class AnalyzeResponse(BaseModel):
    job_id: str
    status: str = "completed"


class ContentMetadata(BaseModel):
    file_count: int = 0
    languages: dict = Field(default_factory=dict)
    frameworks: list = Field(default_factory=list)
    entry_points: list = Field(default_factory=list)


class ContentResponse(BaseModel):
    markdown: str = ""
    mermaid: str = ""
    metadata: ContentMetadata = Field(default_factory=ContentMetadata)
    callgraph: dict = Field(default_factory=dict)
    importgraph: dict = Field(default_factory=dict)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    sources: list[str] = Field(default_factory=list, description="Section titles used as context")


class ErrorResponse(BaseModel):
    detail: str
