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
        if not (
            cleaned_ref.lower().endswith(".pdf") or cleaned_ref.lower().endswith(".txt")
        ):
            raise ValueError("Document reference must refer to a .pdf or .txt file")
        return cleaned_ref


class ScrapeRequest(BaseModel):
    urls: list[str] = Field(
        ...,
        description="List of college website URLs to scrape",
        examples=[["https://www.skcet.ac.in", "https://www.skcet.ac.in/admission"]],
    )
    college_name: str = Field(
        ...,
        description="Name of the college being scraped",
        examples=["SKCET Coimbatore"],
    )


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
            "Number of new chunks successfully generated and inserted into database"
        ),
        examples=[8],
    )
    skipped_chunks: int = Field(
        ...,
        description=(
            "Number of duplicate chunks skipped (due to existing SHA-256 hashes)"
        ),
        examples=[2],
    )
    extracted_text: str = Field(
        ...,
        description="The full extracted text from the PDF document",
        examples=["Coligo College Admission Guidelines\nPage 1..."],
    )


class DocumentItemResponse(BaseModel):
    id: int = Field(..., examples=[1])
    document_ref: str = Field(..., examples=["/path/to/catalog.pdf"])
    chunk_count: int = Field(..., examples=[12])
    created_at: str = Field(..., examples=["2026-08-19T00:00:00Z"])


class DocumentListResponse(BaseModel):
    total: int = Field(..., examples=[3])
    documents: list[DocumentItemResponse]
