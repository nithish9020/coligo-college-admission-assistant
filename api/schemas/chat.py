from typing import List

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        description="The student query/message to ask the counselor",
        examples=["What is the cutoff rank for Sri Krishna College CS branch?"],
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
