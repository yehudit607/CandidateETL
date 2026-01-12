"""Unit tests for gap analyzer service."""

from datetime import date

import pytest

from src.domain.models import Candidate, GapEntry, GapReport, Job
from src.services.gap_analyzer import (
    analyze_gaps,
    calculate_gap_days,
    sort_jobs_chronologically,
)


class TestCalculateGapDays:
    """Tests for calculate_gap_days function."""

    def test_calculates_gap_between_sequential_jobs(self) -> None:
        """Calculates days between job end and next job start."""
        job1 = Job(
            title="Dev",
            company="A",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        job2 = Job(
            title="Senior Dev",
            company="B",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2021, 2, 1),
            end_date=date(2022, 6, 30),
        )

        gap = calculate_gap_days(job1, job2)

        assert gap == 32  # Jan 1 to Feb 1 = 32 days

    def test_returns_one_for_next_day_start(self) -> None:
        """Returns 1 when next job starts the day after previous ends."""
        job1 = Job(
            title="Dev",
            company="A",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 12, 31),
        )
        job2 = Job(
            title="Senior Dev",
            company="B",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2021, 1, 1),
            end_date=date(2022, 6, 30),
        )

        gap = calculate_gap_days(job1, job2)

        assert gap == 1  # Dec 31 to Jan 1 = 1 day gap

    def test_returns_zero_for_overlapping_jobs(self) -> None:
        """Returns 0 when jobs overlap (negative gap becomes 0)."""
        job1 = Job(
            title="Dev",
            company="A",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2020, 1, 1),
            end_date=date(2021, 3, 31),
        )
        job2 = Job(
            title="Senior Dev",
            company="B",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2021, 1, 1),
            end_date=date(2022, 6, 30),
        )

        gap = calculate_gap_days(job1, job2)

        assert gap == 0

    def test_handles_current_job_as_first_job(self) -> None:
        """Handles current job (None end_date) as first job."""
        job1 = Job(
            title="Dev",
            company="A",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2020, 1, 1),
            end_date=None,  # Current job
        )
        job2 = Job(
            title="Senior Dev",
            company="B",
            industry="Tech",
            location="City, ST, US",
            start_date=date(2021, 1, 1),
            end_date=date(2022, 6, 30),
        )

        gap = calculate_gap_days(job1, job2)

        assert gap == 0  # Current job overlaps everything after


class TestSortJobsChronologically:
    """Tests for sort_jobs_chronologically function."""

    def test_sorts_jobs_by_start_date(self) -> None:
        """Sorts jobs in ascending order by start_date."""
        job1 = Job("A", "Corp", "Tech", "City, ST, US", date(2022, 1, 1), date(2022, 12, 31))
        job2 = Job("B", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2020, 12, 31))
        job3 = Job("C", "Corp", "Tech", "City, ST, US", date(2021, 1, 1), date(2021, 12, 31))

        sorted_jobs = sort_jobs_chronologically((job1, job2, job3))

        assert sorted_jobs[0].title == "B"  # 2020
        assert sorted_jobs[1].title == "C"  # 2021
        assert sorted_jobs[2].title == "A"  # 2022

    def test_handles_empty_jobs_list(self) -> None:
        """Returns empty tuple for empty input."""
        sorted_jobs = sort_jobs_chronologically(())

        assert sorted_jobs == ()

    def test_handles_single_job(self) -> None:
        """Returns single job as-is."""
        job = Job("Dev", "Corp", "Tech", "City, ST, US", date(2022, 1, 1), date(2022, 12, 31))

        sorted_jobs = sort_jobs_chronologically((job,))

        assert len(sorted_jobs) == 1
        assert sorted_jobs[0] == job


class TestAnalyzeGaps:
    """Tests for analyze_gaps function."""

    def test_generates_report_with_gap(self) -> None:
        """Generates report with gap entry between jobs."""
        job1 = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2020, 12, 31))
        job2 = Job("Senior", "Corp", "Tech", "City, ST, US", date(2021, 2, 1), date(2022, 6, 30))
        candidate = Candidate("Jane Smith", ("python",), (job2, job1))

        report = analyze_gaps(candidate)

        assert report.candidate_name == "Jane Smith"
        assert len(report.entries) == 3
        assert report.entries[0].entry_type == "job"
        assert report.entries[1].entry_type == "gap"
        assert report.entries[1].gap_days == 32  # Jan 1 to Feb 1
        assert report.entries[2].entry_type == "job"

    def test_generates_report_without_gap_same_day(self) -> None:
        """Generates report without gap entry when next job starts same day."""
        job1 = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2020, 12, 31))
        job2 = Job("Senior", "Corp", "Tech", "City, ST, US", date(2020, 12, 31), date(2022, 6, 30))
        candidate = Candidate("Jane Smith", ("python",), (job1, job2))

        report = analyze_gaps(candidate)

        assert len(report.entries) == 2
        assert all(e.entry_type == "job" for e in report.entries)

    def test_handles_single_job(self) -> None:
        """Generates report with single job entry."""
        job = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2022, 6, 30))
        candidate = Candidate("Jane Smith", ("python",), (job,))

        report = analyze_gaps(candidate)

        assert len(report.entries) == 1
        assert report.entries[0].entry_type == "job"

    def test_handles_no_jobs(self) -> None:
        """Generates empty report for candidate with no jobs."""
        candidate = Candidate("Jane Smith", ("python",), ())

        report = analyze_gaps(candidate)

        assert report.candidate_name == "Jane Smith"
        assert len(report.entries) == 0

    def test_handles_overlapping_jobs(self) -> None:
        """No gap entry for overlapping jobs."""
        job1 = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2021, 6, 30))
        job2 = Job("Senior", "Corp", "Tech", "City, ST, US", date(2021, 1, 1), date(2022, 6, 30))
        candidate = Candidate("Jane Smith", ("python",), (job1, job2))

        report = analyze_gaps(candidate)

        assert len(report.entries) == 2
        assert all(e.entry_type == "job" for e in report.entries)

    def test_gap_entry_contains_correct_message(self) -> None:
        """Gap entry content matches required format."""
        job1 = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2020, 12, 31))
        job2 = Job("Senior", "Corp", "Tech", "City, ST, US", date(2021, 2, 1), date(2022, 6, 30))
        candidate = Candidate("Jane Smith", ("python",), (job1, job2))

        report = analyze_gaps(candidate)

        gap_entry = report.entries[1]
        assert "Gap in CV for 32 days" in gap_entry.content


class TestAnalyzeGapsEdgeCases:
    """Parametrized tests for edge cases."""

    @pytest.mark.parametrize(
        "end_date1,start_date2,expected_gap",
        [
            (date(2020, 12, 31), date(2020, 12, 31), 0),  # Same day start
            (date(2020, 12, 31), date(2021, 1, 2), 2),  # 2 day gap
            (date(2020, 12, 31), date(2021, 2, 1), 32),  # 32 day gap
            (date(2020, 6, 30), date(2021, 1, 1), 185),  # ~6 month gap
        ],
        ids=["same_day", "two_day_gap", "month_gap", "six_month_gap"],
    )
    def test_various_gap_lengths(
        self, end_date1: date, start_date2: date, expected_gap: int
    ) -> None:
        """Tests various gap lengths between jobs."""
        job1 = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), end_date1)
        job2 = Job("Senior", "B", "Tech", "City, ST, US", start_date2, date(2022, 12, 31))
        candidate = Candidate("Test", (), (job1, job2))

        report = analyze_gaps(candidate)

        if expected_gap > 0:
            assert len(report.entries) == 3
            assert report.entries[1].gap_days == expected_gap
        else:
            assert len(report.entries) == 2

    @pytest.mark.parametrize(
        "num_jobs",
        [0, 1],
        ids=["no_jobs", "single_job"],
    )
    def test_various_job_counts_no_gaps(self, num_jobs: int) -> None:
        """Tests report generation with various job counts (no gaps possible)."""
        jobs = []
        for i in range(num_jobs):
            year = 2020 + i
            jobs.append(
                Job(
                    f"Job{i}",
                    f"Company{i}",
                    "Tech",
                    "City, ST, US",
                    date(year, 1, 1),
                    date(year, 12, 31),
                )
            )
        candidate = Candidate("Test", (), tuple(jobs))

        report = analyze_gaps(candidate)

        assert len(report.entries) == num_jobs

    def test_handles_current_job(self) -> None:
        """Handles candidate with current job (None end_date)."""
        job1 = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2020, 12, 31))
        job2 = Job("Senior", "Corp", "Tech", "City, ST, US", date(2021, 2, 1), None)  # Current
        candidate = Candidate("Jane", (), (job1, job2))

        report = analyze_gaps(candidate)

        assert len(report.entries) == 3  # job, gap, current job
        assert report.entries[2].entry_type == "job"
