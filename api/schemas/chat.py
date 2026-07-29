from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        description="The student query/message to ask the counselor",
        examples=["What is the cutoff rank for Sri Krishna College CS branch?"],
    )
    session_id: Optional[str] = Field(
        default=None,
        description=(
            "Opaque conversation id. Pass the same value across requests to keep "
            "context, so follow-ups like 'what about ECE?' are understood. Omit "
            "for a one-off, stateless question."
        ),
        examples=["student-42"],
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Query message cannot be empty")
        return cleaned


class ChatResponse(BaseModel):
    response: str = Field(
        ...,
        description="The NLP processed response answering the query",
        examples=["The cutoff rank for Sri Krishna College CS branch is..."],
    )
    sources: List[str] = Field(
        default_factory=list,
        description="List of document reference sources used to answer the query",
        examples=[["/home/prasanna/Documents/SriKrishna_Admissions.pdf"]],
    )
    session_id: Optional[str] = Field(
        default=None,
        description=(
            "Echoes the session_id from the request. Pass it back on the next "
            "call to continue the conversation. Null when the request was "
            "stateless."
        ),
        examples=["student-42"],
    )
