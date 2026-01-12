"""Candidate filtering service based on criteria."""

from collections.abc import Iterator
from datetime import date

from src.domain.models import Candidate, FilterCriteria


def calculate_total_experience_years(candidate: Candidate) -> float:
    if not candidate.jobs:
        return 0.0

    total_days = 0
    today = date.today()

    for job in candidate.jobs:
        end = job.end_date if job.end_date else today
        duration = (end - job.start_date).days
        total_days += max(0, duration)

    return total_days / 365.25


def has_industry_experience(candidate: Candidate, industry: str) -> bool:
    """Case-insensitive matching."""
    industry_lower = industry.lower()
    return any(job.industry.lower() == industry_lower for job in candidate.jobs)


def has_required_skills(candidate: Candidate, required_skills: tuple[str, ...]) -> bool:
    """AND logic: candidate must have ALL required skills."""
    if not required_skills:
        return True

    candidate_skills = {skill.lower() for skill in candidate.skills}
    required_lower = {skill.lower() for skill in required_skills}

    return required_lower.issubset(candidate_skills)


def matches_criteria(candidate: Candidate, criteria: FilterCriteria) -> bool:
    """AND logic: candidate must match ALL criteria."""
    if not has_industry_experience(candidate, criteria.industry):
        return False

    if not has_required_skills(candidate, criteria.required_skills):
        return False

    experience = calculate_total_experience_years(candidate)
    if experience < criteria.min_years_experience:
        return False

    return True


def filter_candidates(
    candidates: Iterator[Candidate],
    criteria: FilterCriteria,
) -> Iterator[Candidate]:
    for candidate in candidates:
        if matches_criteria(candidate, criteria):
            yield candidate
