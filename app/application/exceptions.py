class UseCaseError(Exception):
    """Base class for application-layer use-case errors."""


class IngestDocumentError(UseCaseError):
    """Base class for ingest document errors."""

class NewOrganizationError(UseCaseError):
    """Base class for new organization errors."""


# --- # Specific use-case errors

class EmptyFileError(IngestDocumentError):
    pass


class UnsupportedFileTypeError(IngestDocumentError):
    pass


class StorageWriteError(IngestDocumentError):
    pass


class StorageDeleteError(IngestDocumentError):
    """Raised only if you want to surface cleanup failures (optional)."""
    pass


class DocumentAlreadyExistsError(IngestDocumentError):
    pass


class ParsingError(IngestDocumentError):
    pass


class ChunkingError(IngestDocumentError):
    pass


class PersistenceError(IngestDocumentError):
    pass

class DocumentPersistError(IngestDocumentError):
    pass

class OrganizationNotFoundError(IngestDocumentError):
    pass

class ChunkPersistenceError(IngestDocumentError):
    pass

# --- #
class OrganizationAlreadyExistsError(NewOrganizationError):
    pass

class InvalidOrganizationNameError(NewOrganizationError):
    pass