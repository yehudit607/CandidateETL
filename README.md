# Candidate Data Processing Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-119%20passing-success.svg)](tests/)
[![Code Style](https://img.shields.io/badge/code%20style-type%20hints-blue.svg)](https://docs.python.org/3/library/typing.html)

An ETL pipeline for analyzing job candidate profiles and filtering candidates based on industry, skills, and experience criteria. Designed to work with HiredScore API data and other standard candidate data formats.

## Features

**Section 1: CV Gap Analysis**
- Fetches candidate data from remote URLs with SSL certificate validation
- Auto-detects and transforms HiredScore API format
- Detects employment gaps between jobs
- Generates formatted work history reports with gap annotations

**Section 2: Smart Filtering & MongoDB Integration**
- Filters candidates by industry (case-insensitive)
- Filters by required skills (AND logic)
- Filters by minimum years of experience
- Persists filtered candidates to MongoDB `filtered_candidates` collection

## Architecture

```
┌─────────────────┐
│  HiredScore API │
│  (Remote URL)   │
└────────┬────────┘
         │ HTTPS (SSL)
         ▼
┌────────────────────────────────────────────────────────┐
│              Data Provider Layer                       │
│  • UrlDataProvider - Fetch & validate JSON            │
│  • DataTransformer - Auto-detect HiredScore format    │
│  • Certificate validation with certifi                │
└────────┬───────────────────────────────────────────────┘
         │ Stream<Candidate>
         ▼
┌────────────────────────────────────────────────────────┐
│               Domain Layer                             │
│  • Candidate (name, skills, jobs)                     │
│  • Job (title, company, industry, dates)              │
│  • FilterCriteria (industry, skills, min_years)       │
└────────┬───────────────────────────────────────────────┘
         │
         ├─────────────────┬────────────────────────────┐
         │                 │                            │
         ▼                 ▼                            ▼
    ┌────────┐      ┌──────────┐              ┌─────────────┐
    │  Gap   │      │  Filter  │              │   Report    │
    │Analyzer│      │  Service │              │  Generator  │
    └────┬───┘      └─────┬────┘              └──────┬──────┘
         │                │                           │
         │                ▼                           │
         │      ┌──────────────────┐                 │
         │      │  Mongo Repository│                 │
         │      │   (persistence)  │                 │
         │      └──────────────────┘                 │
         │                                            │
         └────────────────┬───────────────────────────┘
                          ▼
                   ┌────────────┐
                   │  CLI Main  │
                   │  (commands)│
                   └────────────┘
```

**Key Design Patterns:**
- **Layered Architecture**: Domain → Services → Infrastructure
- **Repository Pattern**: Abstract MongoDB operations
- **Adapter Pattern**: Transform HiredScore format to standard format
- **Generator Pattern**: Memory-efficient streaming with `yield`

## Prerequisites

**Option 1: Docker Only (Recommended)**
- **Docker and Docker Compose** - [Install Docker](https://docs.docker.com/get-docker/)

**Option 2: Local Python**
- **Python 3.11+**
- **Docker and Docker Compose** (for MongoDB)
- **uv** (Python package manager) - Install with: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Quick Setup

### Option 1: Using Docker (Recommended)

**No Python installation required!** Everything runs in containers.

```bash
# 1. Build and start all services (MongoDB + App)
docker-compose up -d

# 2. Run tests
docker-compose run --rm test

# 3. Run CLI commands
docker-compose exec app python -m src.cli.main --help
```

**Development workflow:**
- Source code changes are automatically reflected (volume mounted)
- Run any command: `docker-compose exec app <command>`
- View logs: `docker-compose logs -f app`
- Stop services: `docker-compose down`

### Option 2: Local Python Setup

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

## Data Source

The pipeline works with the HiredScore candidate data:
```bash
DATA_URL="https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json"
```

You can also run the demo scripts for a quick walkthrough:
```bash
# Docker
./examples/demo-docker.sh

# Local Python
./examples/demo.sh
```

## Usage

### Section 1: Generate Gap Analysis Report

Analyze candidate work history and detect employment gaps:

**Using Docker:**
```bash
# Analyze candidates from HiredScore data (text format)
docker-compose exec app python -m src.cli.main analyze "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json"

# Save report to file
docker-compose exec app python -m src.cli.main analyze "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" -o report.txt

# Output in JSON format
docker-compose exec app python -m src.cli.main analyze "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" --format json
```

**Using Local Python:**
```bash
# Analyze candidates from HiredScore data (text format)
uv run python -m src.cli.main analyze "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json"

# Save report to file
uv run python -m src.cli.main analyze "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" -o report.txt

# Output in JSON format
uv run python -m src.cli.main analyze "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" --format json
```

**Expected Output Format:**
```
Hello Clark L Kent,
Worked as: Staff Accountant, From Jan/01/1976 To Dec/31/1998 in New York, NY, US
Gap in CV for 1 days
Worked as: Staff Accountant, From Jan/01/1999 To Jan/01/2002 in Pasadena, AA, US
Worked as: Jigglypuff & Company, C.P.A, From Jan/01/2002 To Dec/31/2002 in Pasadena, AA, US
Gap in CV for 1 days
Worked as: C.O.A.'s, From Jan/01/2003 To Dec/31/2003 in Agrabah, GM, US

Hello Bruce Wayne,
Worked as: Sales/Membership Representative, From Jan/01/2010 To Jan/01/2011 in Atnalta, GA, US
Gap in CV for 69 days
Worked as: Accounts Payable Accountant, From Mar/11/2011 To Jan/01/2012 in Atnalta, GA, US

--- Summary ---
Candidates processed: 4
Employment gaps detected: 9
```

### Section 2: Filter and Archive Candidates

Filter candidates based on criteria and persist matches to MongoDB:

**Using Docker:**
```bash
# Filter candidates in Real Estate industry (will match 2 candidates)
docker-compose exec app python -m src.cli.main filter "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" \
  --industry "Real Estate industry" \
  --min-years 1

# Filter with specific skills (will match 1 candidate)
docker-compose exec app python -m src.cli.main filter "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" \
  --industry "Real Estate industry" \
  --skills "QuickBooks" \
  --min-years 5

# Preview results without saving (dry run)
docker-compose exec app python -m src.cli.main filter "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" \
  --industry "Real Estate industry" \
  --min-years 1 \
  --dry-run
```

**Using Local Python:**
```bash
# Filter candidates in Real Estate industry (will match 2 candidates)
uv run python -m src.cli.main filter "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" \
  --industry "Real Estate industry" \
  --min-years 1

# Filter with specific skills (will match 1 candidate)
uv run python -m src.cli.main filter "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" \
  --industry "Real Estate industry" \
  --skills "QuickBooks" \
  --min-years 5

# Preview results without saving (dry run)
uv run python -m src.cli.main filter "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" \
  --industry "Real Estate industry" \
  --min-years 1 \
  --dry-run

# Custom MongoDB connection
uv run python -m src.cli.main filter "https://recruiting-test-resume-data.hiredscore.com/ps-dev-allcands-full-api_hub_b1f6.json" \
  --industry "Real Estate industry" \
  --min-years 1 \
  --db-uri mongodb://localhost:27017 \
  --db-name my_database
```

**Expected Output:**
```
[INFO] Starting candidate filtering...

--- Summary ---
Candidates processed: 4
Candidates matched: 2
Filter criteria:
  Industry: Real Estate industry
  Skills: (none)
  Min years: 1.0

[PERSISTED] 2 candidates saved to MongoDB.
  Database: candidate_etl
  Collection: filtered_candidates
[MATCH] Clark L Kent
[SKIP]  Bruce Wayne
[MATCH] Peter Parker
[SKIP]  Walter White
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
- **Minimal Dependencies**: Only `pymongo` and `certifi` for runtime; stdlib for everything else
- **Memory Efficient**: Generator-based streaming for large datasets
- **Type Safe**: Full type annotations with mypy validation
- **Immutable**: Frozen dataclasses prevent accidental mutations
- **Layered Architecture**: Clean separation of domain, services, and infrastructure
- **Format Agnostic**: Auto-detects and transforms HiredScore API format to standard format
- **Tested**: Comprehensive unit and integration tests covering business logic and data transformations

## License

MIT License 