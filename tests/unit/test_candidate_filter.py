"""Unit tests for candidate filter service."""

from datetime import date

import pytest

from src.domain.models import Candidate, FilterCriteria, Job
from src.services.candidate_filter import (
    calculate_total_experience_years,
    filter_candidates,
    has_industry_experience,
    has_required_skills,
    matches_criteria,
)


class TestIndustryMatching:
    """Tests for industry matching (case-insensitive)."""

    def test_matches_exact_industry(self) -> None:
        """Matches when candidate has exact industry experience."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2020, 1, 1), date(2022, 12, 31))
        candidate = Candidate("Jane", (), (job,))

        assert has_industry_experience(candidate, "Technology") is True

    def test_matches_case_insensitive(self) -> None:
        """Industry matching is case-insensitive."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2020, 1, 1), date(2022, 12, 31))
        candidate = Candidate("Jane", (), (job,))

        assert has_industry_experience(candidate, "technology") is True
        assert has_industry_experience(candidate, "TECHNOLOGY") is True
        assert has_industry_experience(candidate, "TeCHNoLoGy") is True

    def test_matches_any_job_industry(self) -> None:
        """Matches if any job is in the target industry."""
        job1 = Job("Dev", "Corp", "Finance", "City, ST, US", date(2018, 1, 1), date(2019, 12, 31))
        job2 = Job("Dev", "Corp", "Technology", "City, ST, US", date(2020, 1, 1), date(2022, 12, 31))
        candidate = Candidate("Jane", (), (job1, job2))

        assert has_industry_experience(candidate, "Technology") is True
        assert has_industry_experience(candidate, "Finance") is True

    def test_no_match_for_different_industry(self) -> None:
        """Does not match when candidate lacks industry experience."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2020, 1, 1), date(2022, 12, 31))
        candidate = Candidate("Jane", (), (job,))

        assert has_industry_experience(candidate, "Finance") is False

    def test_no_match_for_no_jobs(self) -> None:
        """Does not match when candidate has no jobs."""
        candidate = Candidate("Jane", (), ())

        assert has_industry_experience(candidate, "Technology") is False


class TestSkillsMatching:
    """Tests for skills matching (AND logic)."""

    def test_matches_single_skill(self) -> None:
        """Matches when candidate has required skill."""
        candidate = Candidate("Jane", ("python", "sql"), ())

        assert has_required_skills(candidate, ("python",)) is True

    def test_matches_all_required_skills(self) -> None:
        """Matches when candidate has all required skills (AND logic)."""
        candidate = Candidate("Jane", ("python", "sql", "docker"), ())

        assert has_required_skills(candidate, ("python", "sql")) is True

    def test_no_match_missing_skill(self) -> None:
        """Does not match when missing any required skill."""
        candidate = Candidate("Jane", ("python", "sql"), ())

        assert has_required_skills(candidate, ("python", "docker")) is False

    def test_matches_case_insensitive(self) -> None:
        """Skills matching is case-insensitive."""
        candidate = Candidate("Jane", ("python", "sql"), ())

        assert has_required_skills(candidate, ("Python",)) is True
        assert has_required_skills(candidate, ("PYTHON",)) is True
        assert has_required_skills(candidate, ("SQL",)) is True

    def test_matches_empty_required_skills(self) -> None:
        """Always matches when no skills are required."""
        candidate = Candidate("Jane", (), ())

        assert has_required_skills(candidate, ()) is True

    def test_no_match_empty_candidate_skills(self) -> None:
        """Does not match when candidate has no skills but skills are required."""
        candidate = Candidate("Jane", (), ())

        assert has_required_skills(candidate, ("python",)) is False


class TestExperienceCalculation:
    """Tests for experience calculation."""

    def test_calculates_single_job_experience(self) -> None:
        """Calculates years from a single job."""
        job = Job("Dev", "Corp", "Tech", "City, ST, US", date(2020, 1, 1), date(2022, 1, 1))
        candidate = Candidate("Jane", (), (job,))

        years = calculate_total_experience_years(candidate)

        assert years == pytest.approx(2.0, rel=0.1)

    def test_calculates_multiple_jobs_experience(self) -> None:
        """Sums experience from multiple jobs."""
        job1 = Job("Dev", "A", "Tech", "City, ST, US", date(2018, 1, 1), date(2020, 1, 1))  # 2 years
        job2 = Job("Senior", "B", "Tech", "City, ST, US", date(2020, 1, 1), date(2023, 1, 1))  # 3 years
        candidate = Candidate("Jane", (), (job1, job2))

        years = calculate_total_experience_years(candidate)

        assert years == pytest.approx(5.0, rel=0.1)

    def test_handles_current_job(self) -> None:
        """Calculates experience including current job up to today."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2020, 1, 1), None)
        candidate = Candidate("Jane", (), (job,))

        years = calculate_total_experience_years(candidate)

        assert years >= 4.0  # At least 4 years from 2020 to now

    def test_handles_no_jobs(self) -> None:
        """Returns 0 for candidate with no jobs."""
        candidate = Candidate("Jane", (), ())

        years = calculate_total_experience_years(candidate)

        assert years == 0.0

    def test_handles_overlapping_jobs(self) -> None:
        """Counts overlapping job periods (no deduplication)."""
        job1 = Job("Dev", "Corp", "Technology", "City, ST, US", date(2020, 1, 1), date(2022, 1, 1))  # 2 years
        job2 = Job("Dev", "Corp", "Technology", "City, ST, US", date(2021, 1, 1), date(2022, 1, 1))  # 1 year
        candidate = Candidate("Jane", (), (job1, job2))

        years = calculate_total_experience_years(candidate)

        assert years == pytest.approx(3.0, rel=0.1)  # Total, not unique


class TestMatchesCriteria:
    """Tests for combined filter criteria matching."""

    def test_matches_all_criteria(self) -> None:
        """Matches when all criteria are satisfied."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))
        candidate = Candidate("Jane", ("python", "sql"), (job,))
        criteria = FilterCriteria("technology", ("python",), 3.0)

        assert matches_criteria(candidate, criteria) is True

    def test_no_match_industry_mismatch(self) -> None:
        """Does not match when industry doesn't match."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))
        candidate = Candidate("Jane", ("python",), (job,))
        criteria = FilterCriteria("finance", ("python",), 3.0)

        assert matches_criteria(candidate, criteria) is False

    def test_no_match_skills_mismatch(self) -> None:
        """Does not match when skills don't match."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))
        candidate = Candidate("Jane", ("java",), (job,))
        criteria = FilterCriteria("technology", ("python",), 3.0)

        assert matches_criteria(candidate, criteria) is False

    def test_no_match_experience_insufficient(self) -> None:
        """Does not match when experience is insufficient."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2022, 1, 1), date(2023, 1, 1))
        candidate = Candidate("Jane", ("python",), (job,))
        criteria = FilterCriteria("technology", ("python",), 5.0)

        assert matches_criteria(candidate, criteria) is False

    @pytest.mark.parametrize(
        "industry,skills,min_years,expected",
        [
            ("technology", ("python",), 2.0, True),
            ("Technology", ("Python",), 2.0, True),  # Case insensitive
            ("finance", ("python",), 2.0, False),  # Wrong industry
            ("technology", ("java",), 2.0, False),  # Missing skill
            ("technology", ("python",), 10.0, False),  # Insufficient exp
            ("technology", (), 2.0, True),  # No skills required
            ("technology", ("python", "sql"), 2.0, True),  # Multiple skills
        ],
        ids=[
            "all_match",
            "case_insensitive",
            "wrong_industry",
            "missing_skill",
            "insufficient_exp",
            "no_skills_required",
            "multiple_skills_match",
        ],
    )
    def test_various_criteria_combinations(
        self,
        industry: str,
        skills: tuple[str, ...],
        min_years: float,
        expected: bool,
    ) -> None:
        """Tests various criteria combinations."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))
        candidate = Candidate("Jane", ("python", "sql"), (job,))
        criteria = FilterCriteria(industry, skills, min_years)

        assert matches_criteria(candidate, criteria) is expected


class TestFilterCandidates:
    """Tests for filter_candidates generator."""

    def test_filters_matching_candidates(self) -> None:
        """Yields only candidates matching criteria."""
        job1 = Job("Dev", "Corp", "Technology", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))
        job2 = Job("Dev", "Corp", "Finance", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))

        candidate1 = Candidate("Jane", ("python",), (job1,))  # Match
        candidate2 = Candidate("John", ("python",), (job2,))  # Wrong industry
        candidate3 = Candidate("Alice", ("java",), (job1,))  # Wrong skills

        candidates = [candidate1, candidate2, candidate3]
        criteria = FilterCriteria("technology", ("python",), 2.0)

        results = list(filter_candidates(iter(candidates), criteria))

        assert len(results) == 1
        assert results[0].name == "Jane"

    def test_returns_generator(self) -> None:
        """Returns a generator for memory-efficient streaming."""
        job = Job("Dev", "Corp", "Technology", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))
        candidate = Candidate("Jane", ("python",), (job,))
        criteria = FilterCriteria("technology", ("python",), 2.0)

        result = filter_candidates(iter([candidate]), criteria)

        from collections.abc import Iterator

        assert isinstance(result, Iterator)

    def test_handles_empty_input(self) -> None:
        """Handles empty candidate iterator."""
        criteria = FilterCriteria("technology", ("python",), 2.0)

        results = list(filter_candidates(iter([]), criteria))

        assert results == []

    def test_all_candidates_filtered_out(self) -> None:
        """Returns empty when no candidates match."""
        job = Job("Dev", "Corp", "Finance", "City, ST, US", date(2018, 1, 1), date(2023, 1, 1))
        candidate = Candidate("Jane", ("python",), (job,))
        criteria = FilterCriteria("technology", ("python",), 2.0)

        results = list(filter_candidates(iter([candidate]), criteria))

        assert results == []
