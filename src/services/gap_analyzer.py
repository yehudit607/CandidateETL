"""Gap analysis service for candidate work history."""

from datetime import date

from src.domain.models import Candidate, GapEntry, GapReport, Job


def calculate_gap_days(job1: Job, job2: Job) -> int:
    """Returns 0 for overlapping or adjacent jobs."""
    if job1.end_date is None:
        return 0

    gap = (job2.start_date - job1.end_date).days
    return max(0, gap)


def sort_jobs_chronologically(jobs: tuple[Job, ...]) -> tuple[Job, ...]:
    return tuple(sorted(jobs, key=lambda j: j.start_date))


def analyze_gaps(candidate: Candidate) -> GapReport:
    if not candidate.jobs:
        return GapReport(candidate_name=candidate.name, entries=())

    sorted_jobs = sort_jobs_chronologically(candidate.jobs)
    entries: list[GapEntry] = []

    for i, job in enumerate(sorted_jobs):
        job_entry = _create_job_entry(job)
        entries.append(job_entry)

        if i < len(sorted_jobs) - 1:
            next_job = sorted_jobs[i + 1]
            gap_days = calculate_gap_days(job, next_job)

            if gap_days > 0:
                gap_entry = _create_gap_entry(gap_days)
                entries.append(gap_entry)

    return GapReport(candidate_name=candidate.name, entries=tuple(entries))


def _create_job_entry(job: Job) -> GapEntry:
    """Create a job entry for the gap report matching specification format.

    Format: "Worked as: [Title], From [Date] To [Date] in [Location]"
    Date format: "Jan/20/2013" (Month abbreviation/day/year)
    """
    start_str = _format_date(job.start_date)
    end_str = _format_date(job.end_date) if job.end_date else "Present"

    content = f"Worked as: {job.title}, From {start_str} To {end_str} in {job.location}"
    return GapEntry(entry_type="job", content=content, gap_days=None)


def _format_date(d: date) -> str:
    """Format date as 'Jan/20/2013' per specification."""
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    return f"{months[d.month-1]}/{d.day:02d}/{d.year}"


def _create_gap_entry(gap_days: int) -> GapEntry:
    content = f"Gap in CV for {gap_days} days"
    return GapEntry(entry_type="gap", content=content, gap_days=gap_days)
