"""Unit tests for report generator service."""

import json
from datetime import date

import pytest

from src.domain.models import GapEntry, GapReport
from src.services.report_generator import format_gap_report_json, format_gap_report_text


class TestFormatGapReportText:
    """Tests for format_gap_report_text function."""

    def test_formats_empty_report(self) -> None:
        """Formats report with no entries."""
        report = GapReport("Jane Smith", ())

        output = format_gap_report_text(report)

        assert "Jane Smith" in output
        assert "No work history" in output or len(output.split("\n")) <= 3

    def test_formats_single_job_entry(self) -> None:
        """Formats report with single job entry."""
        entry = GapEntry(
            entry_type="job",
            content="Software Engineer at TechCorp (2020-01-15 to 2022-06-30)",
        )
        report = GapReport("Jane Smith", (entry,))

        output = format_gap_report_text(report)

        assert "Jane Smith" in output
        assert "Software Engineer" in output
        assert "TechCorp" in output

    def test_formats_job_with_gap(self) -> None:
        """Formats report with job and gap entries."""
        job1 = GapEntry(
            entry_type="job",
            content="Analyst at DataCo (2018-03-01 to 2019-12-31)",
        )
        gap = GapEntry(
            entry_type="gap",
            content="Gap in CV for 15 days",
            gap_days=15,
        )
        job2 = GapEntry(
            entry_type="job",
            content="Engineer at TechCorp (2020-01-15 to 2022-06-30)",
        )
        report = GapReport("Jane Smith", (job1, gap, job2))

        output = format_gap_report_text(report)

        assert "Jane Smith" in output
        assert "Analyst" in output
        assert "Gap in CV for 15 days" in output
        assert "Engineer" in output

    def test_preserves_chronological_order(self) -> None:
        """Output maintains chronological order of entries."""
        job1 = GapEntry(entry_type="job", content="First Job")
        gap = GapEntry(entry_type="gap", content="Gap", gap_days=10)
        job2 = GapEntry(entry_type="job", content="Second Job")
        report = GapReport("Test", (job1, gap, job2))

        output = format_gap_report_text(report)

        first_idx = output.find("First Job")
        gap_idx = output.find("Gap")
        second_idx = output.find("Second Job")
        assert first_idx < gap_idx < second_idx

    def test_formats_multiple_gaps(self) -> None:
        """Formats report with multiple gaps."""
        entries = (
            GapEntry(entry_type="job", content="Job 1"),
            GapEntry(entry_type="gap", content="Gap in CV for 30 days", gap_days=30),
            GapEntry(entry_type="job", content="Job 2"),
            GapEntry(entry_type="gap", content="Gap in CV for 45 days", gap_days=45),
            GapEntry(entry_type="job", content="Job 3"),
        )
        report = GapReport("Jane", entries)

        output = format_gap_report_text(report)

        assert "Gap in CV for 30 days" in output
        assert "Gap in CV for 45 days" in output


class TestFormatGapReportJson:
    """Tests for format_gap_report_json function."""

    def test_returns_valid_json(self) -> None:
        """Returns valid JSON string."""
        report = GapReport("Jane Smith", ())

        output = format_gap_report_json(report)

        parsed = json.loads(output)
        assert isinstance(parsed, dict)

    def test_includes_candidate_name(self) -> None:
        """JSON includes candidate name."""
        report = GapReport("Jane Smith", ())

        output = format_gap_report_json(report)
        parsed = json.loads(output)

        assert parsed["candidate_name"] == "Jane Smith"

    def test_includes_entries_array(self) -> None:
        """JSON includes entries array."""
        entry = GapEntry(entry_type="job", content="Test Job")
        report = GapReport("Jane", (entry,))

        output = format_gap_report_json(report)
        parsed = json.loads(output)

        assert "entries" in parsed
        assert isinstance(parsed["entries"], list)
        assert len(parsed["entries"]) == 1

    def test_entry_includes_type_and_content(self) -> None:
        """JSON entries include type and content."""
        entry = GapEntry(entry_type="job", content="Engineer at Corp")
        report = GapReport("Jane", (entry,))

        output = format_gap_report_json(report)
        parsed = json.loads(output)

        entry_data = parsed["entries"][0]
        assert entry_data["entry_type"] == "job"
        assert entry_data["content"] == "Engineer at Corp"

    def test_gap_entry_includes_gap_days(self) -> None:
        """Gap entries include gap_days field."""
        entry = GapEntry(entry_type="gap", content="Gap in CV", gap_days=15)
        report = GapReport("Jane", (entry,))

        output = format_gap_report_json(report)
        parsed = json.loads(output)

        entry_data = parsed["entries"][0]
        assert entry_data["gap_days"] == 15

    def test_job_entry_gap_days_is_null(self) -> None:
        """Job entries have null gap_days."""
        entry = GapEntry(entry_type="job", content="Job")
        report = GapReport("Jane", (entry,))

        output = format_gap_report_json(report)
        parsed = json.loads(output)

        entry_data = parsed["entries"][0]
        assert entry_data["gap_days"] is None

    def test_preserves_entry_order(self) -> None:
        """JSON entries maintain original order."""
        entries = (
            GapEntry(entry_type="job", content="First"),
            GapEntry(entry_type="gap", content="Gap", gap_days=10),
            GapEntry(entry_type="job", content="Second"),
        )
        report = GapReport("Jane", entries)

        output = format_gap_report_json(report)
        parsed = json.loads(output)

        assert parsed["entries"][0]["content"] == "First"
        assert parsed["entries"][1]["content"] == "Gap"
        assert parsed["entries"][2]["content"] == "Second"


class TestReportFormatConsistency:
    """Tests for consistency between text and JSON formats."""

    def test_both_formats_handle_empty_report(self) -> None:
        """Both formats handle empty report without error."""
        report = GapReport("Test", ())

        text_output = format_gap_report_text(report)
        json_output = format_gap_report_json(report)

        assert "Test" in text_output
        assert "Test" in json_output

    @pytest.mark.parametrize(
        "num_entries",
        [1, 3, 5, 10],
        ids=["one_entry", "three_entries", "five_entries", "ten_entries"],
    )
    def test_both_formats_handle_various_entry_counts(self, num_entries: int) -> None:
        """Both formats handle various entry counts."""
        entries = tuple(
            GapEntry(entry_type="job", content=f"Job {i}") for i in range(num_entries)
        )
        report = GapReport("Test", entries)

        text_output = format_gap_report_text(report)
        json_output = format_gap_report_json(report)
        parsed_json = json.loads(json_output)

        for i in range(num_entries):
            assert f"Job {i}" in text_output
        assert len(parsed_json["entries"]) == num_entries
