class DocustreamError(Exception):
    """Base exception for DOCUSTREAM."""
    pass


class ConversionError(DocustreamError):
    pass


class StorageError(DocustreamError):
    pass


class JobNotFoundError(DocustreamError):
    pass
