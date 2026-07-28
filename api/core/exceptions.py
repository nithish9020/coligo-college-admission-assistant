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
