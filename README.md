# Candidate Data Processing Pipeline

A Python 3.11 ETL pipeline for analyzing job candidate profiles and filtering candidates based on industry, skills, and experience criteria.

## Features

**Section 1: CV Gap Analysis**
- Fetches candidate data from remote URLs
- Detects employment gaps between jobs
- Generates formatted work history reports with gap annotations

**Section 2: Smart Filtering & MongoDB Integration**
- Filters candidates by industry (case-insensitive)
- Filters by required skills (AND logic)
- Filters by minimum years of experience
- Persists filtered candidates to MongoDB `filtered_candidates` collection

## Prerequisites

- **Python 3.11+**
- **Docker and Docker Compose** (for MongoDB)
- **uv** (Python package manager) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Quick Setup

### 1. Install Dependencies

```bash
# Install the package with development dependencies
uv pip install -e ".[dev]"
```

### 2. Start MongoDB

```bash
# Start MongoDB container using Docker Compose
docker-compose up -d

# Verify MongoDB is running
docker-compose ps
# Should show: mongodb ... Up
```

### 3. Verify Installation

```bash
# Run tests to verify setup
uv run pytest tests/ -v

# Check CLI is accessible
uv run python -m src.cli.main --help
```

## Usage

### Section 1: Generate Gap Analysis Report

Analyze candidate work history and detect employment gaps:

```bash
# Analyze candidates from a URL (text format)
uv run python -m src.cli.main analyze <URL>

# Save report to file
uv run python -m src.cli.main analyze <URL> -o report.txt

# Output in JSON format
uv run python -m src.cli.main analyze <URL> --format json
```

**Expected Output Format:**
```
Hello Jane Smith,
Worked as: Data Analyst, From Mar/01/2018 To Dec/31/2019 in Newark, NJ, US
Gap in CV for 60 days
Worked as: Data Scientist, From Mar/01/2020 To Present in New York, NY, US

--- Summary ---
Candidates processed: 1
Employment gaps detected: 1
```

### Section 2: Filter and Archive Candidates

Filter candidates based on criteria and persist matches to MongoDB:

```bash
# Filter for Python developers with 3+ years in Technology
uv run python -m src.cli.main filter <URL> \
  --industry Technology \
  --skills "Python,SQL" \
  --min-years 3

# Preview results without saving (dry run)
uv run python -m src.cli.main filter <URL> \
  --industry Technology \
  --skills Python \
  --min-years 2 \
  --dry-run

# Custom MongoDB connection
uv run python -m src.cli.main filter <URL> \
  --industry Finance \
  --skills "Excel,SQL" \
  --min-years 5 \
  --db-uri mongodb://localhost:27017 \
  --db-name my_database
```

**Expected Output:**
```
[INFO] Starting candidate filtering...
[MATCH] Jane Smith
[SKIP]  John Doe

--- Summary ---
Candidates processed: 2
Candidates matched: 1
Filter criteria:
  Industry: Technology
  Skills: Python, SQL
  Min years: 3.0

[PERSISTED] 1 candidates saved to MongoDB.
  Database: candidate_etl
  Collection: filtered_candidates
```

## Sample Data Format

Create a test JSON file (`candidates.json`):

```json
{
  "candidates": [
    {
      "name": "Jane Smith",
      "skills": ["Python", "SQL", "Machine Learning"],
      "jobs": [
        {
          "title": "Data Scientist",
          "company": "TechCorp",
          "industry": "Technology",
          "location": "New York, NY, US",
          "start_date": "2021-03-01",
          "end_date": null
        },
        {
          "title": "Junior Analyst",
          "company": "DataCo",
          "industry": "Technology",
          "location": "Newark, NJ, US",
          "start_date": "2019-06-15",
          "end_date": "2020-12-31"
        }
      ]
    }
  ]
}
```

### Testing Locally

```bash
# Start a simple HTTP server
uv run python -m http.server 8000 &

# Run analyze command against local data
uv run python -m src.cli.main analyze http://localhost:8000/candidates.json

# Stop the server
kill %1
```

## Verify Database Results

```bash
# Connect to MongoDB
docker exec -it candidateetl-mongodb-1 mongosh

# In mongosh:
use candidate_etl
db.filtered_candidates.find().pretty()
db.filtered_candidates.countDocuments()
```

## Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit/test_gap_analyzer.py -v

# Run with coverage
uv run pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Environment Variables

Configure MongoDB connection via environment variables:

```bash
export MONGODB_URI="mongodb://localhost:27017"
export MONGODB_DATABASE="candidate_etl"

# Run filter command (uses environment variables)
uv run python -m src.cli.main filter <URL> --industry Tech --skills Python --min-years 2
```

## Project Structure

```
CandidateETL/
├── src/
│   ├── domain/          # Business entities (Job, Candidate, FilterCriteria)
│   ├── services/        # Business logic (gap analysis, filtering)
│   ├── infrastructure/  # External concerns (data provider, MongoDB repository)
│   └── cli/            # Command-line interface
├── tests/
│   ├── unit/           # Unit tests with mocked dependencies
│   └── integration/    # End-to-end pipeline tests
├── docker-compose.yml  # MongoDB service configuration
├── pyproject.toml     # Project dependencies and configuration
└── README.md          # This file
```

## Troubleshooting

### MongoDB Connection Failed

```bash
# Check if container is running
docker-compose ps

# Restart if needed
docker-compose down && docker-compose up -d

# Check logs
docker-compose logs mongodb
```

### Import Errors

```bash
# Ensure you're using uv run
uv run python -m src.cli.main --help

# Or activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python -m src.cli.main --help
```

### URL Fetch Errors

```bash
# Test URL accessibility
curl -I <URL>

# Verify JSON format
curl <URL> | python -m json.tool
```

## Design Principles

- **Python 3.11**: Leveraging modern type hints and `dataclasses`
- **Minimal Dependencies**: Only `pymongo` for runtime; stdlib for everything else
- **Memory Efficient**: Generator-based streaming for large datasets
- **Type Safe**: Full type annotations with mypy validation
- **Immutable**: Frozen dataclasses prevent accidental mutations
- **Layered Architecture**: Clean separation of domain, services, and infrastructure
- **Tested**: 100+ unit and integration tests with 97-100% coverage on business logic

## License

MIT License - See LICENSE file for details

## Author

CandidateETL Team
