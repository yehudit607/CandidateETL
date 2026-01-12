"""Unit tests for UrlDataProvider."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import DataFetchError, DataParseError
from src.domain.models import Candidate, Job
from src.infrastructure.data_provider import UrlDataProvider


class TestUrlDataProviderInit:
    """Tests for UrlDataProvider initialization."""

    @pytest.mark.parametrize(
        "url,timeout,expected_timeout",
        [
            ("https://example.com/data.json", None, 30),  # Default timeout
            ("https://example.com/data.json", 60, 60),  # Custom timeout
        ],
        ids=["default_timeout", "custom_timeout"],
    )
    def test_initialization(self, url: str, timeout: int | None, expected_timeout: int) -> None:
        """Provider initializes with URL and timeout."""
        provider = UrlDataProvider(url) if timeout is None else UrlDataProvider(url, timeout=timeout)
        assert provider.url == url
        assert provider.timeout == expected_timeout


class TestUrlDataProviderStreamCandidates:
    """Tests for stream_candidates() generator."""

    @patch("src.infrastructure.data_provider.urlopen")
    def test_stream_single_candidate(self, mock_urlopen: MagicMock) -> None:
        """Streams a single candidate from JSON response."""
        json_data = {
            "candidates": [
                {
                    "name": "Jane Smith",
                    "skills": ["Python", "SQL"],
                    "jobs": [
                        {
                            "title": "Engineer",
                            "company": "TechCorp",
                            "industry": "Technology",
                            "start_date": "2020-01-15",
                            "end_date": "2022-06-30",
                        }
                    ],
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        assert len(candidates) == 1
        assert candidates[0].name == "Jane Smith"
        assert candidates[0].skills == ("python", "sql")
        assert len(candidates[0].jobs) == 1
        assert candidates[0].jobs[0].title == "Engineer"

    @patch("src.infrastructure.data_provider.urlopen")
    def test_stream_multiple_candidates(self, mock_urlopen: MagicMock) -> None:
        """Streams multiple candidates from JSON response."""
        json_data = {
            "candidates": [
                {
                    "name": "Alice",
                    "skills": ["Java"],
                    "jobs": [],
                },
                {
                    "name": "Bob",
                    "skills": ["Python"],
                    "jobs": [],
                },
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        assert len(candidates) == 2
        assert candidates[0].name == "Alice"
        assert candidates[1].name == "Bob"

    @patch("src.infrastructure.data_provider.urlopen")
    def test_stream_candidate_with_current_job(self, mock_urlopen: MagicMock) -> None:
        """Parses job with null end_date as current position."""
        json_data = {
            "candidates": [
                {
                    "name": "Jane",
                    "skills": [],
                    "jobs": [
                        {
                            "title": "Developer",
                            "company": "StartupXYZ",
                            "industry": "Technology",
                            "start_date": "2022-07-01",
                            "end_date": None,
                        }
                    ],
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        assert candidates[0].jobs[0].end_date is None

    @patch("src.infrastructure.data_provider.urlopen")
    def test_skills_normalized_to_lowercase(self, mock_urlopen: MagicMock) -> None:
        """Skills are normalized to lowercase for matching."""
        json_data = {
            "candidates": [
                {
                    "name": "Jane",
                    "skills": ["Python", "MACHINE LEARNING", "SQL"],
                    "jobs": [],
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        assert candidates[0].skills == ("python", "machine learning", "sql")


class TestUrlDataProviderNetworkErrors:
    """Tests for network error handling."""

    @patch("src.infrastructure.data_provider.urlopen")
    def test_raises_data_fetch_error_on_url_error(
        self, mock_urlopen: MagicMock
    ) -> None:
        """Raises DataFetchError when URL cannot be reached."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        provider = UrlDataProvider("https://example.com/data.json")

        with pytest.raises(DataFetchError) as exc_info:
            list(provider.stream_candidates())

        assert "Connection refused" in str(exc_info.value)

    @patch("src.infrastructure.data_provider.urlopen")
    def test_raises_data_fetch_error_on_http_error(
        self, mock_urlopen: MagicMock
    ) -> None:
        """Raises DataFetchError on HTTP error responses."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(
            url="https://example.com",
            code=404,
            msg="Not Found",
            hdrs={},  # type: ignore[arg-type]
            fp=None,
        )

        provider = UrlDataProvider("https://example.com/data.json")

        with pytest.raises(DataFetchError) as exc_info:
            list(provider.stream_candidates())

        assert "404" in str(exc_info.value)

    @patch("src.infrastructure.data_provider.urlopen")
    def test_raises_data_fetch_error_on_timeout(self, mock_urlopen: MagicMock) -> None:
        """Raises DataFetchError when request times out."""
        from socket import timeout

        mock_urlopen.side_effect = timeout("Connection timed out")

        provider = UrlDataProvider("https://example.com/data.json", timeout=5)

        with pytest.raises(DataFetchError) as exc_info:
            list(provider.stream_candidates())

        assert "timed out" in str(exc_info.value).lower()


class TestUrlDataProviderJsonParsing:
    """Parametrized tests for JSON parsing edge cases."""

    @patch("src.infrastructure.data_provider.urlopen")
    def test_raises_data_parse_error_on_invalid_json(
        self, mock_urlopen: MagicMock
    ) -> None:
        """Raises DataParseError when response is not valid JSON."""
        mock_response = MagicMock()
        mock_response.read.return_value = b"not valid json"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")

        with pytest.raises(DataParseError):
            list(provider.stream_candidates())

    @patch("src.infrastructure.data_provider.urlopen")
    def test_raises_data_parse_error_on_missing_candidates_key(
        self, mock_urlopen: MagicMock
    ) -> None:
        """Raises DataParseError when JSON lacks 'candidates' key."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"data": []}).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")

        with pytest.raises(DataParseError) as exc_info:
            list(provider.stream_candidates())

        assert "candidates" in str(exc_info.value).lower()

    @pytest.mark.parametrize(
        "invalid_candidate,expected_error",
        [
            ({"skills": [], "jobs": []}, "name"),
            ({"name": "", "skills": [], "jobs": []}, "name"),
            ({"name": "Jane", "jobs": []}, "skills"),
            ({"name": "Jane", "skills": []}, "jobs"),
        ],
        ids=[
            "missing_name",
            "empty_name",
            "missing_skills",
            "missing_jobs",
        ],
    )
    @patch("src.infrastructure.data_provider.urlopen")
    def test_skips_malformed_candidate_records(
        self,
        mock_urlopen: MagicMock,
        invalid_candidate: dict,
        expected_error: str,
    ) -> None:
        """Skips malformed candidate records and continues processing."""
        json_data = {
            "candidates": [
                invalid_candidate,
                {"name": "Valid", "skills": ["python"], "jobs": []},
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        assert len(candidates) == 1
        assert candidates[0].name == "Valid"

    @pytest.mark.parametrize(
        "invalid_job",
        [
            {"title": "Dev", "company": "Corp", "industry": "Tech", "start_date": "2020-01-01"},
            {"title": "", "company": "Corp", "industry": "Tech", "start_date": "2020-01-01", "end_date": None},
            {"title": "Dev", "company": "", "industry": "Tech", "start_date": "2020-01-01", "end_date": None},
            {"title": "Dev", "company": "Corp", "industry": "", "start_date": "2020-01-01", "end_date": None},
            {"title": "Dev", "company": "Corp", "industry": "Tech", "start_date": "invalid-date", "end_date": None},
        ],
        ids=[
            "missing_end_date_key",
            "empty_title",
            "empty_company",
            "empty_industry",
            "invalid_date_format",
        ],
    )
    @patch("src.infrastructure.data_provider.urlopen")
    def test_skips_candidate_with_invalid_job(
        self,
        mock_urlopen: MagicMock,
        invalid_job: dict,
    ) -> None:
        """Skips candidates with malformed job records."""
        json_data = {
            "candidates": [
                {"name": "Invalid", "skills": [], "jobs": [invalid_job]},
                {"name": "Valid", "skills": [], "jobs": []},
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        assert len(candidates) == 1
        assert candidates[0].name == "Valid"

    @patch("src.infrastructure.data_provider.urlopen")
    def test_handles_empty_candidates_list(self, mock_urlopen: MagicMock) -> None:
        """Returns empty generator when candidates list is empty."""
        json_data = {"candidates": []}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        assert candidates == []

    @patch("src.infrastructure.data_provider.urlopen")
    def test_parses_dates_correctly(self, mock_urlopen: MagicMock) -> None:
        """Parses ISO date strings into date objects."""
        json_data = {
            "candidates": [
                {
                    "name": "Jane",
                    "skills": [],
                    "jobs": [
                        {
                            "title": "Dev",
                            "company": "Corp",
                            "industry": "Tech",
                            "start_date": "2020-03-15",
                            "end_date": "2022-12-31",
                        }
                    ],
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/data.json")
        candidates = list(provider.stream_candidates())

        job = candidates[0].jobs[0]
        assert job.start_date == date(2020, 3, 15)
        assert job.end_date == date(2022, 12, 31)
