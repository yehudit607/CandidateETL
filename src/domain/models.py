from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True)
class Job:
    """Represents a single employment period in a candidate's work history."""

    title: str
    company: str
    industry: str
    location: str
    start_date: date
    end_date: date | None = None


@dataclass(frozen=True)
class Candidate:
    """Represents a job applicant with their profile and work history."""

    name: str
    skills: tuple[str, ...]
    jobs: tuple[Job, ...]


@dataclass(frozen=True)
class FilterCriteria:
    """Represents parameters for filtering candidates."""

    industry: str
    required_skills: tuple[str, ...]
    min_years_experience: float


@dataclass(frozen=True)
class GapEntry:
    """Represents a single entry in a gap analysis report."""

    entry_type: Literal["job", "gap"]
    content: str
    gap_days: int | None = None


@dataclass(frozen=True)
class GapReport:
    """Represents the complete gap analysis output for a single candidate."""

    candidate_name: str
    entries: tuple[GapEntry, ...]
