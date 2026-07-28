from pydantic import BaseModel, Field, field_validator


class DocumentProcessRequest(BaseModel):
    document_ref: str = Field(
        ...,
        description="Path to local PDF file or URL to a PDF file",
        examples=[
            "/path/to/college_catalog.pdf",
            "https://example.com/admission_guidelines.pdf",
        ],
    )

    @field_validator("document_ref")
    @classmethod
    def validate_document_ref(cls, v: str) -> str:
        cleaned_ref = v.strip()
        if not cleaned_ref:
            raise ValueError("Document reference cannot be empty")
        if not cleaned_ref.lower().endswith(".pdf"):
            raise ValueError("Document reference must refer to a PDF file (.pdf)")
        return cleaned_ref


class DocumentProcessResponse(BaseModel):
    document_ref: str = Field(
        ...,
        description="The document reference that was processed",
        examples=["/path/to/college_catalog.pdf"],
    )
    total_chunks: int = Field(
        ...,
        description="Total number of chunks generated from the document",
        examples=[10],
    )
    inserted_chunks: int = Field(
        ...,
        description=(
            "Number of new chunks successfully " "generated and inserted into database"
        ),
        examples=[8],
    )
    skipped_chunks: int = Field(
        ...,
        description=(
            "Number of duplicate chunks skipped " "(due to existing SHA-256 hashes)"
        ),
        examples=[2],
    )
    extracted_text: str = Field(
        ...,
        description="The full extracted text from the PDF document",
        examples=["Coligo College Admission Guidelines\nPage 1..."],
    )
