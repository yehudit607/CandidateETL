"""Domain exceptions for the Candidate ETL Pipeline."""


class CandidateETLError(Exception):
    """Base exception for all Candidate ETL errors."""


class DataFetchError(CandidateETLError):
    """Raised when data cannot be fetched from a remote source."""


class DataParseError(CandidateETLError):
    """Raised when data cannot be parsed into expected format."""


class RepositoryError(CandidateETLError):
    """Raised when a repository operation fails."""
