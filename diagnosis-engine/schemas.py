from pydantic import BaseModel, Field
from typing import List, Optional

class FaultyCodeBlock(BaseModel):
    file: str
    function: str
    line_start: int
    line_end: int
    code_snippet: str

class SimilarIncident(BaseModel):
    incident_id: str
    similarity: float
    resolution: str

class SuggestedFix(BaseModel):
    type: str = Field(..., description="'code_patch' or 'rollback'")
    diff: str = Field(..., description="unified diff of the fix")
    rollback_target_tag: str = Field(..., description="tag to rollback to if applicable")

class RCAResult(BaseModel):
    incident_id: str
    root_cause: str
    faulty_code_block: FaultyCodeBlock
    confidence_score: float
    similar_historical_incidents: List[SimilarIncident] = []
    suggested_fix: SuggestedFix
    requires_human_approval: bool = True
    status: str = "AWAITING_APPROVAL"
