"""Integration tests for the full Candidate ETL Pipeline."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.domain.models import Candidate, FilterCriteria, Job
from src.infrastructure.data_provider import UrlDataProvider
from src.infrastructure.repository import MongoRepository
from src.services.candidate_filter import filter_candidates, matches_criteria
from src.services.gap_analyzer import analyze_gaps


class TestEndToEndPipeline:
    """End-to-end integration tests for the full pipeline."""

    @patch("src.infrastructure.data_provider.urlopen")
    def test_full_gap_analysis_pipeline(self, mock_urlopen: MagicMock) -> None:
        """Tests complete flow: fetch -> parse -> analyze -> report."""
        json_data = {
            "candidates": [
                {
                    "name": "Jane Smith",
                    "skills": ["Python", "SQL"],
                    "jobs": [
                        {
                            "title": "Junior Dev",
                            "company": "StartupA",
                            "industry": "Technology",
                            "start_date": "2018-01-01",
                            "end_date": "2019-12-31",
                        },
                        {
                            "title": "Senior Dev",
                            "company": "TechCorp",
                            "industry": "Technology",
                            "start_date": "2020-06-01",
                            "end_date": "2023-12-31",
                        },
                    ],
                }
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/candidates.json")
        candidates = list(provider.stream_candidates())

        assert len(candidates) == 1

        report = analyze_gaps(candidates[0])

        assert report.candidate_name == "Jane Smith"
        assert len(report.entries) == 3
        gap_entries = [e for e in report.entries if e.entry_type == "gap"]
        assert len(gap_entries) == 1
        assert gap_entries[0].gap_days > 0

    @patch("src.infrastructure.data_provider.urlopen")
    def test_full_filter_pipeline(self, mock_urlopen: MagicMock) -> None:
        """Tests complete flow: fetch -> parse -> filter."""
        json_data = {
            "candidates": [
                {
                    "name": "Jane (Match)",
                    "skills": ["Python", "SQL"],
                    "jobs": [
                        {
                            "title": "Dev",
                            "company": "TechCorp",
                            "industry": "Technology",
                            "start_date": "2018-01-01",
                            "end_date": "2023-12-31",
                        }
                    ],
                },
                {
                    "name": "John (No Match - Industry)",
                    "skills": ["Python"],
                    "jobs": [
                        {
                            "title": "Analyst",
                            "company": "FinCorp",
                            "industry": "Finance",
                            "start_date": "2020-01-01",
                            "end_date": "2023-12-31",
                        }
                    ],
                },
                {
                    "name": "Alice (No Match - Skills)",
                    "skills": ["Java"],
                    "jobs": [
                        {
                            "title": "Dev",
                            "company": "TechCorp",
                            "industry": "Technology",
                            "start_date": "2020-01-01",
                            "end_date": "2023-12-31",
                        }
                    ],
                },
            ]
        }
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(json_data).encode("utf-8")
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        provider = UrlDataProvider("https://example.com/candidates.json")
        criteria = FilterCriteria("technology", ("python",), 3.0)

        filtered = list(filter_candidates(provider.stream_candidates(), criteria))

        assert len(filtered) == 1
        assert filtered[0].name == "Jane (Match)"

    @patch("src.infrastructure.repository.MongoClient")
    @patch("src.infrastructure.data_provider.urlopen")
    def test_full_persistence_pipeline(
        self, mock_urlopen: MagicMock, mock_client_class: MagicMock
    ) -> None:
        """Tests complete flow: fetch -> filter -> persist."""
        json_data = {
            "candidates": [
                {
                    "name": "Jane Smith",
                    "skills": ["Python"],
                    "jobs": [
                        {
                            "title": "Dev",
                            "company": "TechCorp",
                            "industry": "Technology",
                            "start_date": "2018-01-01",
                            "end_date": "2023-12-31",
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

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.insert_many.return_value = MagicMock(inserted_ids=["id1"])
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        provider = UrlDataProvider("https://example.com/candidates.json")
        criteria = FilterCriteria("technology", ("python",), 3.0)
        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        candidates = list(provider.stream_candidates())
        matched = [c for c in candidates if matches_criteria(c, criteria)]

        saved = repo.save_filtered_candidates(matched, criteria)

        assert saved == 1
        mock_collection.insert_many.assert_called_once()


class TestMongoRepositoryIntegration:
    """Integration tests for MongoDB repository (requires running MongoDB)."""

    @pytest.mark.skip(reason="Requires running MongoDB instance")
    def test_save_and_retrieve_candidates(self) -> None:
        """Tests full save and retrieve cycle with real MongoDB."""
        repo = MongoRepository("mongodb://localhost:27017", "test_integration")

        try:
            repo.clear_filtered_candidates()

            job = Job("\1", "\2", "\3", "City, ST, US", date(2020, 1, 1), date(2023, 12, 31))
            candidates = [
                Candidate("Jane", ("python",), (job,)),
                Candidate("John", ("java",), (job,)),
            ]
            criteria = FilterCriteria("tech", ("python",), 2.0)

            saved = repo.save_filtered_candidates(candidates, criteria)
            assert saved == 2

            retrieved = repo.get_filtered_candidates()
            assert len(retrieved) == 2

            cleared = repo.clear_filtered_candidates()
            assert cleared == 2
        finally:
            repo.clear_filtered_candidates()
