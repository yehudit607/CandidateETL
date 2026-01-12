"""Repository implementations for candidate persistence."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from pymongo import MongoClient
from pymongo.errors import PyMongoError

from src.domain.exceptions import RepositoryError
from src.domain.models import Candidate, FilterCriteria, Job


class CandidateRepository(ABC):
    """Abstract base class for candidate persistence.

    Implements the Repository Pattern per Constitution Principle I
    (Dependency Inversion) to decouple business logic from storage.
    """

    @abstractmethod
    def save_filtered_candidates(
        self,
        candidates: Sequence[Candidate],
        criteria: FilterCriteria,
    ) -> int:
        """Raises RepositoryError on failure."""

    @abstractmethod
    def get_filtered_candidates(self, limit: int | None = None) -> list[Candidate]:
        """Raises RepositoryError on failure."""

    @abstractmethod
    def clear_filtered_candidates(self) -> int:
        """Raises RepositoryError on failure."""


class MongoRepository(CandidateRepository):
    """MongoDB implementation of CandidateRepository.

    Uses pymongo for database operations per Constitution Principle II.
    Uses bulk operations (insert_many) per Constitution Principle III.
    """

    COLLECTION_NAME = "filtered_candidates"

    def __init__(self, connection_uri: str, database_name: str) -> None:
        self._client = MongoClient(connection_uri)
        self._database_name = database_name
        self._db = self._client[database_name]
        self._collection = self._db[self.COLLECTION_NAME]

    def save_filtered_candidates(
        self,
        candidates: Sequence[Candidate],
        criteria: FilterCriteria,
    ) -> int:
        if not candidates:
            return 0

        documents = [
            self._candidate_to_document(candidate, criteria)
            for candidate in candidates
        ]

        try:
            result = self._collection.insert_many(documents)
            return len(result.inserted_ids)
        except PyMongoError as e:
            raise RepositoryError(f"Failed to save candidates: {e}") from e

    def get_filtered_candidates(self, limit: int | None = None) -> list[Candidate]:
        try:
            cursor = self._collection.find()
            if limit is not None:
                cursor = cursor.limit(limit)

            return [self._document_to_candidate(doc) for doc in cursor]
        except PyMongoError as e:
            raise RepositoryError(f"Failed to retrieve candidates: {e}") from e

    def clear_filtered_candidates(self) -> int:
        try:
            result = self._collection.delete_many({})
            return result.deleted_count
        except PyMongoError as e:
            raise RepositoryError(f"Failed to clear candidates: {e}") from e

    def _candidate_to_document(
        self, candidate: Candidate, criteria: FilterCriteria
    ) -> dict[str, Any]:
        return {
            "name": candidate.name,
            "skills": list(candidate.skills),
            "jobs": [self._job_to_dict(job) for job in candidate.jobs],
            "filter_metadata": {
                "filtered_at": datetime.utcnow().isoformat(),
                "criteria": {
                    "industry": criteria.industry,
                    "required_skills": criteria.required_skills,
                    "min_years_experience": criteria.min_years_experience,
                },
            },
        }

    def _job_to_dict(self, job: Job) -> dict[str, Any]:
        return {
            "title": job.title,
            "company": job.company,
            "industry": job.industry,
            "location": job.location,
            "start_date": str(job.start_date),
            "end_date": str(job.end_date) if job.end_date else None,
        }

    def _document_to_candidate(self, doc: dict[str, Any]) -> Candidate:
        jobs = tuple(self._dict_to_job(job_dict) for job_dict in doc.get("jobs", []))
        return Candidate(
            name=doc["name"],
            skills=tuple(doc.get("skills", [])),
            jobs=jobs,
        )

    def _dict_to_job(self, job_dict: dict[str, Any]) -> Job:
        return Job(
            title=job_dict["title"],
            company=job_dict["company"],
            industry=job_dict["industry"],
            location=job_dict.get("location", "Unknown"),
            start_date=date.fromisoformat(job_dict["start_date"]),
            end_date=(
                date.fromisoformat(job_dict["end_date"])
                if job_dict.get("end_date")
                else None
            ),
        )
