"""Unit tests for HiredScore data transformer."""

import json

import pytest

from src.infrastructure.data_transformer import (
    _convert_date_to_iso,
    _extract_jobs,
    _extract_name,
    _extract_skills,
    load_and_transform_hiredscore_json,
    transform_hiredscore_to_standard,
)


class TestExtractName:
    """Tests for name extraction from HiredScore format."""

    def test_extracts_formatted_name(self) -> None:
        """Extracts formatted_name from contact_info.name dict."""
        data = {
            "contact_info": {"name": {"formatted_name": "John Doe", "given_name": "John", "family_name": "Doe"}}
        }
        assert _extract_name(data, 0) == "John Doe"

    def test_constructs_from_given_family_name(self) -> None:
        """Constructs name from given_name and family_name when formatted_name missing."""
        data = {"contact_info": {"name": {"given_name": "Jane", "family_name": "Smith"}}}
        assert _extract_name(data, 0) == "Jane Smith"

    def test_falls_back_to_candidate_number(self) -> None:
        """Falls back to 'Candidate N' when no name available."""
        data = {"contact_info": {}}
        assert _extract_name(data, 0) == "Candidate 1"
        assert _extract_name(data, 5) == "Candidate 6"

    def test_handles_missing_contact_info(self) -> None:
        """Handles missing contact_info."""
        data = {}
        assert _extract_name(data, 0) == "Candidate 1"


class TestExtractSkills:
    """Tests for skills extraction from HiredScore format."""

    def test_extracts_from_extracted_skills_objects(self) -> None:
        """Extracts skill_name from extracted_skills objects."""
        data = {"extracted_skills": [{"skill_name": "Python"}, {"skill_name": "SQL"}]}
        assert _extract_skills(data) == ["Python", "SQL"]

    def test_extracts_from_extracted_skills_strings(self) -> None:
        """Extracts skills when extracted_skills contains strings."""
        data = {"extracted_skills": ["Python", "SQL", "Docker"]}
        assert _extract_skills(data) == ["Python", "SQL", "Docker"]

    def test_falls_back_to_resume_skills(self) -> None:
        """Falls back to resume_skills when extracted_skills empty."""
        data = {"extracted_skills": [], "resume_skills": ["Java", "Spring"]}
        assert _extract_skills(data) == ["Java", "Spring"]

    def test_returns_empty_when_no_skills(self) -> None:
        """Returns empty list when no skills available."""
        data = {}
        assert _extract_skills(data) == []


class TestConvertDateToIso:
    """Tests for HiredScore date format conversion."""

    def test_converts_valid_date(self) -> None:
        """Converts HiredScore date format to ISO format."""
        assert _convert_date_to_iso("Jan/01/2008") == "2008-01-01"
        assert _convert_date_to_iso("Dec/31/2022") == "2022-12-31"
        assert _convert_date_to_iso("Mar/15/2020") == "2020-03-15"

    def test_returns_none_for_invalid_date(self) -> None:
        """Returns None for invalid date formats."""
        assert _convert_date_to_iso("invalid") is None
        assert _convert_date_to_iso("2020-01-01") is None
        assert _convert_date_to_iso("") is None


class TestExtractJobs:
    """Tests for job extraction from HiredScore experience array."""

    def test_extracts_job_with_all_fields(self) -> None:
        """Extracts job with all fields present."""
        data = {
            "experience": [
                {
                    "title": "Software Engineer",
                    "company_name": "TechCorp",
                    "company_details": {"industry": "Technology"},
                    "location": {"short_display_address": "New York, NY, US"},
                    "start_date": "Jan/01/2020",
                    "end_date": "Dec/31/2022",
                }
            ]
        }
        jobs = _extract_jobs(data)
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Software Engineer"
        assert jobs[0]["company"] == "TechCorp"
        assert jobs[0]["industry"] == "Technology"
        assert jobs[0]["location"] == "New York, NY, US"
        assert jobs[0]["start_date"] == "2020-01-01"
        assert jobs[0]["end_date"] == "2022-12-31"

    def test_handles_current_job_with_no_end_date(self) -> None:
        """Handles current jobs with None end_date."""
        data = {
            "experience": [
                {
                    "title": "Engineer",
                    "company_name": "Corp",
                    "start_date": "Jan/01/2020",
                    "end_date": None,
                }
            ]
        }
        jobs = _extract_jobs(data)
        assert len(jobs) == 1
        assert jobs[0]["end_date"] is None

    def test_skips_job_with_missing_required_fields(self) -> None:
        """Skips jobs missing required fields."""
        data = {
            "experience": [
                {"title": "Engineer"},  # Missing company_name and start_date
                {
                    "title": "Dev",
                    "company_name": "Corp",
                    "start_date": "Jan/01/2020",
                    "end_date": "Dec/31/2022",
                },
            ]
        }
        jobs = _extract_jobs(data)
        assert len(jobs) == 1  # Only the complete job

    def test_defaults_to_unknown_for_optional_fields(self) -> None:
        """Uses 'Unknown' for missing optional fields."""
        data = {
            "experience": [
                {
                    "title": "Engineer",
                    "company_name": "Corp",
                    "start_date": "Jan/01/2020",
                    "end_date": "Dec/31/2022",
                }
            ]
        }
        jobs = _extract_jobs(data)
        assert jobs[0]["industry"] == "Unknown"
        assert jobs[0]["location"] == "Unknown"


class TestTransformHiredscore:
    """Tests for HiredScore to standard format transformation."""

    def test_transforms_complete_candidate(self) -> None:
        """Transforms a complete HiredScore candidate record."""
        hiredscore_data = [
            {
                "contact_info": {"name": {"formatted_name": "Alice Johnson"}},
                "extracted_skills": [{"skill_name": "Python"}, {"skill_name": "SQL"}],
                "experience": [
                    {
                        "title": "Data Scientist",
                        "company_name": "DataCo",
                        "company_details": {"industry": "Technology"},
                        "location": {"short_display_address": "Boston, MA, US"},
                        "start_date": "Jan/01/2020",
                        "end_date": "Dec/31/2022",
                    }
                ],
            }
        ]

        result = transform_hiredscore_to_standard(hiredscore_data)

        assert "candidates" in result
        assert len(result["candidates"]) == 1

        candidate = result["candidates"][0]
        assert candidate["name"] == "Alice Johnson"
        assert candidate["skills"] == ["Python", "SQL"]
        assert len(candidate["jobs"]) == 1
        assert candidate["jobs"][0]["title"] == "Data Scientist"

    def test_transforms_multiple_candidates(self) -> None:
        """Transforms multiple candidates."""
        hiredscore_data = [
            {"contact_info": {"name": {"formatted_name": "Alice"}}, "extracted_skills": [], "experience": []},
            {"contact_info": {"name": {"formatted_name": "Bob"}}, "extracted_skills": [], "experience": []},
        ]

        result = transform_hiredscore_to_standard(hiredscore_data)

        assert len(result["candidates"]) == 2
        assert result["candidates"][0]["name"] == "Alice"
        assert result["candidates"][1]["name"] == "Bob"


class TestLoadAndTransform:
    """Tests for load_and_transform_hiredscore_json."""

    def test_transforms_hiredscore_list_format(self) -> None:
        """Transforms HiredScore list format."""
        json_content = json.dumps(
            [
                {
                    "contact_info": {"name": {"formatted_name": "Test User"}},
                    "extracted_skills": ["Skill1"],
                    "experience": [],
                }
            ]
        )

        result = load_and_transform_hiredscore_json(json_content)

        assert "candidates" in result
        assert len(result["candidates"]) == 1
        assert result["candidates"][0]["name"] == "Test User"

    def test_returns_standard_format_unchanged(self) -> None:
        """Returns standard format unchanged."""
        json_content = json.dumps({"candidates": [{"name": "Test", "skills": [], "jobs": []}]})

        result = load_and_transform_hiredscore_json(json_content)

        assert "candidates" in result
        assert result["candidates"][0]["name"] == "Test"

    def test_raises_on_unknown_format(self) -> None:
        """Raises ValueError for unknown JSON format."""
        json_content = json.dumps({"unknown": "format"})

        with pytest.raises(ValueError, match="Unknown JSON format"):
            load_and_transform_hiredscore_json(json_content)
