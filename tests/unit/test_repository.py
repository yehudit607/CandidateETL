"""Unit tests for MongoRepository with mocked pymongo."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest

from src.domain.exceptions import RepositoryError
from src.domain.models import Candidate, FilterCriteria, Job
from src.infrastructure.repository import MongoRepository


class TestMongoRepositoryInit:
    """Tests for MongoRepository initialization."""

    @patch("src.infrastructure.repository.MongoClient")
    def test_init_creates_client_with_uri(self, mock_client_class: MagicMock) -> None:
        """Initializes MongoClient with provided URI."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        mock_client_class.assert_called_once_with("mongodb://localhost:27017")
        assert repo._database_name == "test_db"

    @patch("src.infrastructure.repository.MongoClient")
    def test_init_accesses_collection(self, mock_client_class: MagicMock) -> None:
        """Accesses the filtered_candidates collection."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        mock_client.__getitem__.assert_called_once_with("test_db")
        mock_db.__getitem__.assert_called_once_with("filtered_candidates")


class TestSaveFilteredCandidates:
    """Tests for save_filtered_candidates method."""

    @patch("src.infrastructure.repository.MongoClient")
    def test_saves_candidates_with_insert_many(
        self, mock_client_class: MagicMock
    ) -> None:
        """Uses insert_many for bulk save operation."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.insert_many.return_value = MagicMock(inserted_ids=["id1", "id2"])
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        job = Job("\1", "\2", "\3", "City, ST, US", date(2020, 1, 1), date(2022, 12, 31))
        candidates = [
            Candidate("Jane", ("python",), (job,)),
            Candidate("John", ("java",), (job,)),
        ]
        criteria = FilterCriteria("tech", ("python",), 2.0)

        result = repo.save_filtered_candidates(candidates, criteria)

        assert result == 2
        mock_collection.insert_many.assert_called_once()

    @patch("src.infrastructure.repository.MongoClient")
    def test_saves_empty_list_returns_zero(
        self, mock_client_class: MagicMock
    ) -> None:
        """Returns 0 when saving empty candidate list."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        criteria = FilterCriteria("tech", ("python",), 2.0)
        result = repo.save_filtered_candidates([], criteria)

        assert result == 0
        mock_collection.insert_many.assert_not_called()

    @patch("src.infrastructure.repository.MongoClient")
    def test_document_includes_filter_metadata(
        self, mock_client_class: MagicMock
    ) -> None:
        """Saved documents include filter_metadata with timestamp and criteria."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.insert_many.return_value = MagicMock(inserted_ids=["id1"])
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        job = Job("\1", "\2", "\3", "City, ST, US", date(2020, 1, 1), date(2022, 12, 31))
        candidates = [Candidate("Jane", ("python",), (job,))]
        criteria = FilterCriteria("tech", ("python",), 2.0)

        repo.save_filtered_candidates(candidates, criteria)

        call_args = mock_collection.insert_many.call_args
        documents = call_args[0][0]
        assert len(documents) == 1
        doc = documents[0]

        assert "filter_metadata" in doc
        assert "filtered_at" in doc["filter_metadata"]
        assert doc["filter_metadata"]["criteria"]["industry"] == "tech"
        assert doc["filter_metadata"]["criteria"]["required_skills"] == ("python",)
        assert doc["filter_metadata"]["criteria"]["min_years_experience"] == 2.0

    @patch("src.infrastructure.repository.MongoClient")
    def test_raises_repository_error_on_failure(
        self, mock_client_class: MagicMock
    ) -> None:
        """Raises RepositoryError when insert_many fails."""
        from pymongo.errors import PyMongoError

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.insert_many.side_effect = PyMongoError("Connection failed")
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        job = Job("\1", "\2", "\3", "City, ST, US", date(2020, 1, 1), date(2022, 12, 31))
        candidates = [Candidate("Jane", ("python",), (job,))]
        criteria = FilterCriteria("tech", ("python",), 2.0)

        with pytest.raises(RepositoryError):
            repo.save_filtered_candidates(candidates, criteria)


class TestGetFilteredCandidates:
    """Tests for get_filtered_candidates method."""

    @patch("src.infrastructure.repository.MongoClient")
    def test_returns_candidates_from_collection(
        self, mock_client_class: MagicMock
    ) -> None:
        """Returns candidates from the collection."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.find.return_value = [
            {
                "name": "Jane",
                "skills": ["python"],
                "jobs": [
                    {
                        "title": "Dev",
                        "company": "Corp",
                        "industry": "Tech",
                        "start_date": "2020-01-01",
                        "end_date": "2022-12-31",
                    }
                ],
            }
        ]
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        candidates = repo.get_filtered_candidates()

        assert len(candidates) == 1
        assert candidates[0].name == "Jane"

    @patch("src.infrastructure.repository.MongoClient")
    def test_applies_limit(self, mock_client_class: MagicMock) -> None:
        """Applies limit parameter to query."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.limit.return_value = []
        mock_collection.find.return_value = mock_cursor
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        repo.get_filtered_candidates(limit=10)

        mock_cursor.limit.assert_called_once_with(10)

    @patch("src.infrastructure.repository.MongoClient")
    def test_raises_repository_error_on_failure(
        self, mock_client_class: MagicMock
    ) -> None:
        """Raises RepositoryError when find fails."""
        from pymongo.errors import PyMongoError

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.find.side_effect = PyMongoError("Query failed")
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        with pytest.raises(RepositoryError):
            repo.get_filtered_candidates()


class TestClearFilteredCandidates:
    """Tests for clear_filtered_candidates method."""

    @patch("src.infrastructure.repository.MongoClient")
    def test_deletes_all_documents(self, mock_client_class: MagicMock) -> None:
        """Deletes all documents from collection."""
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.delete_many.return_value = MagicMock(deleted_count=5)
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        result = repo.clear_filtered_candidates()

        assert result == 5
        mock_collection.delete_many.assert_called_once_with({})

    @patch("src.infrastructure.repository.MongoClient")
    def test_raises_repository_error_on_failure(
        self, mock_client_class: MagicMock
    ) -> None:
        """Raises RepositoryError when delete fails."""
        from pymongo.errors import PyMongoError

        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_collection.delete_many.side_effect = PyMongoError("Delete failed")
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        mock_client_class.return_value = mock_client

        repo = MongoRepository("mongodb://localhost:27017", "test_db")

        with pytest.raises(RepositoryError):
            repo.clear_filtered_candidates()
