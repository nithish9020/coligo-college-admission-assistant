from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import get_db
from api.core.deps import AuthenticatedUser, get_current_college, get_current_user
from api.core.exceptions import NotAuthorizedError
from api.core.logging import get_logger
from api.schemas.brochure import BrochureResponse, BrochureUpdate
from api.schemas.brochure_extraction import (
    ApplyBrochureExtractionRequest,
    BrochureExtractionResult,
)
from api.schemas.college import CollegeDetailResponse
from api.services.brochure_extraction_service import extract_brochure_details
from api.services.brochure_service import (
    delete_brochure,
    get_brochure_for_download,
    list_brochures,
    update_brochure,
    upload_brochure,
)
from api.services.college_service import apply_brochure_extraction, get_college_detail

router = APIRouter(prefix="/brochures", tags=["Brochures"])
logger = get_logger(__name__)


@router.get(
    "",
    response_model=list[BrochureResponse],
    summary="List brochures (own college, or ?college_id= for admins)",
)
async def get_brochures(
    college_id: int | None = Query(
        None, description="Required for admin callers; ignored for college callers"
    ),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[BrochureResponse]:
    if user.role == "college":
        target_college_id = user.college_id
    else:
        if college_id is None:
            raise NotAuthorizedError("college_id query param is required for admins")
        target_college_id = college_id

    brochures = await list_brochures(db, target_college_id)  # type: ignore[arg-type]
    return [BrochureResponse.model_validate(b) for b in brochures]


@router.post(
    "",
    response_model=BrochureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new PDF brochure for the logged-in college",
)
async def add_brochure(
    title: str = Form(...),
    category: str | None = Form(None),
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> BrochureResponse:
    content = await file.read()
    brochure = await upload_brochure(
        db,
        user.college_id,  # type: ignore[arg-type]
        title,
        category,
        file.filename or "brochure.pdf",
        content,
    )
    return BrochureResponse.model_validate(brochure)


@router.put(
    "/{brochure_id}",
    response_model=BrochureResponse,
    summary="Update brochure title/category (owned by the logged-in college)",
)
async def edit_brochure(
    brochure_id: int,
    data: BrochureUpdate,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> BrochureResponse:
    brochure = await update_brochure(db, user.college_id, brochure_id, data)  # type: ignore[arg-type]
    return BrochureResponse.model_validate(brochure)


@router.delete(
    "/{brochure_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a brochure owned by the logged-in college",
)
async def remove_brochure(
    brochure_id: int,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_brochure(db, user.college_id, brochure_id)  # type: ignore[arg-type]


@router.get(
    "/{brochure_id}/download",
    summary="Download a brochure PDF (owned college, or any brochure for admins)",
)
async def download_brochure(
    brochure_id: int,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    owner_scope = user.college_id if user.role == "college" else None
    brochure = await get_brochure_for_download(db, brochure_id, owner_scope)
    return FileResponse(
        brochure.file_path,
        media_type="application/pdf",
        filename=f"{brochure.title}.pdf",
    )


@router.post(
    "/{brochure_id}/extract",
    response_model=BrochureExtractionResult,
    summary="Extract suggested college/course/facility details from a brochure",
)
async def extract_brochure(
    brochure_id: int,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> BrochureExtractionResult:
    """Runs OpenAI over the brochure's PDF text and returns a suggestion —
    nothing is written to the database here. The college reviews/edits the
    result client-side and confirms it via POST .../apply-extraction."""
    brochure = await get_brochure_for_download(db, brochure_id, user.college_id)
    with open(brochure.file_path, "rb") as f:
        pdf_bytes = f.read()
    result = await extract_brochure_details(pdf_bytes)
    return BrochureExtractionResult.model_validate(result)


@router.post(
    "/{brochure_id}/apply-extraction",
    response_model=CollegeDetailResponse,
    summary="Apply reviewed brochure extraction results to the college",
)
async def apply_extraction(
    brochure_id: int,
    data: ApplyBrochureExtractionRequest,
    user: AuthenticatedUser = Depends(get_current_college),
    db: AsyncSession = Depends(get_db),
) -> CollegeDetailResponse:
    # Confirms the brochure exists and is owned by the caller before writing
    # anything, even though the extraction payload itself doesn't reference it.
    await get_brochure_for_download(db, brochure_id, user.college_id)
    await apply_brochure_extraction(db, user.college_id, data)  # type: ignore[arg-type]
    return await get_college_detail(db, user.college_id)  # type: ignore[arg-type]
