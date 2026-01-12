"""Shared test fixtures for the Candidate ETL Pipeline."""

from datetime import date

import pytest

from src.domain.models import Candidate, FilterCriteria, GapEntry, GapReport, Job


@pytest.fixture
def sample_job_tech() -> Job:
    """A sample tech industry job."""
    return Job(
        title="Software Engineer",
        company="TechCorp",
        industry="Technology",
        location="New York, NY, US",
        start_date=date(2020, 1, 15),
        end_date=date(2022, 6, 30),
    )


@pytest.fixture
def sample_job_finance() -> Job:
    """A sample finance industry job."""
    return Job(
        title="Data Analyst",
        company="FinanceInc",
        industry="Finance",
        location="Newark, NJ, US",
        start_date=date(2018, 3, 1),
        end_date=date(2019, 12, 31),
    )


@pytest.fixture
def sample_job_current() -> Job:
    """A sample current job (no end date)."""
    return Job(
        title="Senior Developer",
        company="StartupXYZ",
        industry="Technology",
        location="San Francisco, CA, US",
        start_date=date(2022, 7, 1),
        end_date=None,
    )


@pytest.fixture
def sample_candidate_with_gap(
    sample_job_tech: Job, sample_job_finance: Job
) -> Candidate:
    """A candidate with a gap between jobs."""
    return Candidate(
        name="Jane Smith",
        skills=("python", "sql", "machine learning"),
        jobs=(sample_job_finance, sample_job_tech),
    )


@pytest.fixture
def sample_candidate_no_gap(sample_job_tech: Job, sample_job_current: Job) -> Candidate:
    """A candidate with continuous employment."""
    return Candidate(
        name="John Doe",
        skills=("java", "spring", "kubernetes"),
        jobs=(sample_job_tech, sample_job_current),
    )


@pytest.fixture
def sample_candidate_single_job(sample_job_current: Job) -> Candidate:
    """A candidate with only one job."""
    return Candidate(
        name="Alice Johnson",
        skills=("react", "typescript"),
        jobs=(sample_job_current,),
    )


@pytest.fixture
def sample_candidate_no_jobs() -> Candidate:
    """A candidate with no work history."""
    return Candidate(
        name="Bob Wilson",
        skills=("python",),
        jobs=(),
    )


@pytest.fixture
def sample_filter_criteria_tech() -> FilterCriteria:
    """Filter criteria for tech industry with Python skill."""
    return FilterCriteria(
        industry="technology",
        required_skills=("python",),
        min_years_experience=2.0,
    )


@pytest.fixture
def sample_filter_criteria_finance() -> FilterCriteria:
    """Filter criteria for finance industry."""
    return FilterCriteria(
        industry="finance",
        required_skills=("sql",),
        min_years_experience=1.0,
    )


@pytest.fixture
def sample_gap_entry_job() -> GapEntry:
    """A sample job entry in a gap report."""
    return GapEntry(
        entry_type="job",
        content="Worked as: Software Engineer, From Jan/15/2020 To Jun/30/2022 in New York, NY, US",
        gap_days=None,
    )


@pytest.fixture
def sample_gap_entry_gap() -> GapEntry:
    """A sample gap entry in a gap report."""
    return GapEntry(
        entry_type="gap",
        content="Gap in CV for 15 days",
        gap_days=15,
    )


@pytest.fixture
def sample_gap_report(
    sample_gap_entry_job: GapEntry, sample_gap_entry_gap: GapEntry
) -> GapReport:
    """A sample gap analysis report."""
    return GapReport(
        candidate_name="Jane Smith",
        entries=(sample_gap_entry_job, sample_gap_entry_gap),
    )


@pytest.fixture
def sample_candidates_list(
    sample_candidate_with_gap: Candidate,
    sample_candidate_no_gap: Candidate,
    sample_candidate_single_job: Candidate,
) -> list[Candidate]:
    """A list of sample candidates for batch testing."""
    return [
        sample_candidate_with_gap,
        sample_candidate_no_gap,
        sample_candidate_single_job,
    ]
