"""Data providers for candidate data ingestion."""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Iterator
from datetime import date
from socket import timeout as SocketTimeout
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from src.domain.exceptions import DataFetchError, DataParseError
from src.domain.models import Candidate, Job

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Abstract base class for candidate data providers.

    Implementations must use generators for memory-efficient streaming
    per Constitution Principle III (Performance & Scalability).
    """

    @abstractmethod
    def stream_candidates(self) -> Iterator[Candidate]:
        """Raises DataFetchError or DataParseError on failure."""


class UrlDataProvider(DataProvider):
    """Fetches candidate data from a remote URL.

    Uses urllib.request for HTTP operations per Constitution Principle II
    (Minimal Dependencies - prefer Standard Library).
    """

    def __init__(self, url: str, timeout: int = 30) -> None:
        self.url = url
        self.timeout = timeout

    def stream_candidates(self) -> Iterator[Candidate]:
        data = self._fetch_json()
        candidates_data = self._extract_candidates_list(data)

        for candidate_data in candidates_data:
            candidate = self._parse_candidate(candidate_data)
            if candidate is not None:
                yield candidate

    def _fetch_json(self) -> dict[str, Any]:
        try:
            with urlopen(self.url, timeout=self.timeout) as response:
                raw_data = response.read()
                return json.loads(raw_data.decode("utf-8"))
        except HTTPError as e:
            raise DataFetchError(f"HTTP error {e.code}: {e.msg}") from e
        except URLError as e:
            raise DataFetchError(f"Failed to fetch URL: {e.reason}") from e
        except SocketTimeout as e:
            raise DataFetchError(f"Request timed out: {e}") from e
        except json.JSONDecodeError as e:
            raise DataParseError(f"Invalid JSON: {e}") from e

    def _extract_candidates_list(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        if "candidates" not in data:
            raise DataParseError("JSON response missing 'candidates' key")
        return data["candidates"]

    def _parse_candidate(self, data: dict[str, Any]) -> Candidate | None:
        """Parse a single candidate from JSON data. Returns None if invalid."""
        try:
            name = data.get("name", "")
            if not name or not name.strip():
                logger.warning("Skipping candidate with missing or empty name")
                return None

            if "skills" not in data:
                logger.warning("Skipping candidate '%s': missing skills field", name)
                return None

            if "jobs" not in data:
                logger.warning("Skipping candidate '%s': missing jobs field", name)
                return None

            skills = tuple(skill.lower() for skill in data["skills"])
            jobs = self._parse_jobs(data["jobs"], name)
            if jobs is None:
                return None

            return Candidate(name=name, skills=skills, jobs=jobs)
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("Skipping malformed candidate record: %s", e)
            return None

    def _parse_jobs(
        self, jobs_data: list[dict[str, Any]], candidate_name: str
    ) -> tuple[Job, ...] | None:
        """Parse jobs list. Returns None if any job is invalid."""
        jobs: list[Job] = []
        for job_data in jobs_data:
            job = self._parse_job(job_data, candidate_name)
            if job is None:
                return None
            jobs.append(job)
        return tuple(jobs)

    def _parse_job(
        self, data: dict[str, Any], candidate_name: str
    ) -> Job | None:
        """Parse a single job from JSON data. Returns None if invalid."""
        try:
            title = data.get("title", "")
            company = data.get("company", "")
            industry = data.get("industry", "")
            location = data.get("location", "Unknown")

            if not title or not company or not industry:
                logger.warning(
                    "Skipping candidate '%s': job has empty required field",
                    candidate_name,
                )
                return None

            if "end_date" not in data:
                logger.warning(
                    "Skipping candidate '%s': job missing end_date key",
                    candidate_name,
                )
                return None

            start_date = date.fromisoformat(data["start_date"])
            end_date = (
                date.fromisoformat(data["end_date"]) if data["end_date"] else None
            )

            return Job(
                title=title,
                company=company,
                industry=industry,
                location=location,
                start_date=start_date,
                end_date=end_date,
            )
        except (KeyError, ValueError) as e:
            logger.warning(
                "Skipping candidate '%s': invalid job data - %s", candidate_name, e
            )
            return None
