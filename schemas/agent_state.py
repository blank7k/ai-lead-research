from typing import Annotated, List, Optional
from pydantic import BaseModel, Field
from models.domain import Lead


def merge_list(left: List[str], right: List[str]) -> List[str]:
    """Helper reducer to append items in lists in LangGraph state."""
    return left + right


class AgentState(BaseModel):
    """LangGraph State representation for the Dynamic Research Agent workflow."""
    
    # Core lead object carrying current harvested details, missing fields, and machine trace
    lead: Lead = Field(..., description="The current lead model holding gathered contacts/socials.")
    
    # Dynamic routing controls
    next_tool: Optional[str] = Field(
        None, 
        description="The identifier of the next tool to run, computed by the Decision Engine."
    )
    
    # Detailed human-readable execution trace logs shown to user
    trace_logs: Annotated[List[str], merge_list] = Field(
        default_factory=list,
        description="Human-readable summaries of executed tool steps and decision points."
    )
    
    # System logs / debugging info
    logs: Annotated[List[str], merge_list] = Field(
        default_factory=list,
        description="Internal agent reasoning thoughts."
    )
