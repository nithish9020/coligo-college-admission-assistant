class DocumentProcessingError(Exception):
    """Base exception class for document processing errors."""

    pass


class InvalidDocumentRefError(DocumentProcessingError):
    """Raised when the document reference is invalid."""

    pass


class DocumentNotFoundError(DocumentProcessingError):
    """Raised when the document could not be found or retrieved."""

    pass


class CorruptedDocumentError(DocumentProcessingError):
    """Raised when the document is corrupted or failed to parse."""

    pass


class EmptyDocumentTextError(DocumentProcessingError):
    """Raised when no readable text could be extracted from the document."""

    pass


class BrochureExtractionError(DocumentProcessingError):
    """Raised when OpenAI brochure detail extraction is misconfigured or fails."""

    pass


class AdministrationPortalError(Exception):
    """Base exception class for administration portal (auth/college) errors."""

    pass


class DuplicateEmailError(AdministrationPortalError):
    """Raised when signing up with an email that is already registered."""

    pass


class InvalidCredentialsError(AdministrationPortalError):
    """Raised when login credentials are incorrect."""

    pass


class NotAuthenticatedError(AdministrationPortalError):
    """Raised when a request has a missing/invalid/expired auth token."""

    pass


class NotAuthorizedError(AdministrationPortalError):
    """Raised when an authenticated user lacks permission for an action."""

    pass


class ResourceNotFoundError(AdministrationPortalError):
    """Raised when a requested college/course/facility/brochure doesn't exist."""

    pass


class InvalidFileError(AdministrationPortalError):
    """Raised when an uploaded file fails type/size validation."""

    pass
