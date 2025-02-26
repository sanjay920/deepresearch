from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class WorkspaceQuery(BaseModel):
    """Model for natural language queries to the workspace agent."""

    query: str = Field(
        ..., description="Natural language query for document operations"
    )


class DocumentOperation(BaseModel):
    """Model for document operation results."""

    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Description of the operation result")
    file_name: Optional[str] = Field(
        None, description="Name of the file that was operated on"
    )
    section_name: Optional[str] = Field(
        None, description="Name of the section that was operated on"
    )
    content: Optional[str] = Field(
        None, description="Content that was added or modified"
    )
