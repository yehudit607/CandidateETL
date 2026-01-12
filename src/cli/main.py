import argparse
import os
import sys
from pathlib import Path

from src.domain.exceptions import DataFetchError, DataParseError, RepositoryError
from src.domain.models import Candidate, FilterCriteria
from src.infrastructure.data_provider import UrlDataProvider
from src.infrastructure.repository import MongoRepository
from src.services.candidate_filter import matches_criteria
from src.services.gap_analyzer import analyze_gaps
from src.services.report_generator import format_gap_report_json, format_gap_report_text

DEFAULT_DB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_DB_NAME = os.environ.get("MONGODB_DATABASE", "candidate_etl")


def format_error(error_type: str, message: str, suggestion: str | None = None) -> str:
    lines = [f"[ERROR] {error_type}: {message}"]
    if suggestion:
        lines.append(f"        Suggestion: {suggestion}")
    return "\n".join(lines)


def print_progress(count: int, operation: str) -> None:
    """Print progress indicator for long-running operations.

    Args:
        count: Current count of processed items.
        operation: Description of the operation (e.g., "candidates analyzed").
    """
    if count % 100 == 0 and count > 0:
        print(f"  [PROGRESS] {count} {operation}...", file=sys.stderr)


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="candidate-etl",
        description="Candidate Data Processing Pipeline - Analyze and filter job applicants",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyze candidate work history for employment gaps"
    )
    analyze_parser.add_argument("url", help="URL to fetch candidate data from")
    analyze_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output file path (default: stdout)",
    )
    analyze_parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    filter_parser = subparsers.add_parser(
        "filter", help="Filter candidates by industry, skills, and experience"
    )
    filter_parser.add_argument("url", help="URL to fetch candidate data from")
    filter_parser.add_argument(
        "--industry",
        "-i",
        required=True,
        help="Target industry (case-insensitive)",
    )
    filter_parser.add_argument(
        "--skills",
        "-s",
        default="",
        help="Comma-separated list of required skills (AND logic)",
    )
    filter_parser.add_argument(
        "--min-years",
        "-y",
        type=float,
        default=0.0,
        help="Minimum years of experience (default: 0)",
    )
    filter_parser.add_argument(
        "--dry-run",
        "-d",
        action="store_true",
        help="Preview results without persistence",
    )
    filter_parser.add_argument(
        "--db-uri",
        default=DEFAULT_DB_URI,
        help=f"MongoDB connection URI (default: {DEFAULT_DB_URI})",
    )
    filter_parser.add_argument(
        "--db-name",
        default=DEFAULT_DB_NAME,
        help=f"MongoDB database name (default: {DEFAULT_DB_NAME})",
    )

    return parser


def run_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze command."""
    provider = UrlDataProvider(args.url)

    candidates_processed = 0
    gaps_detected = 0
    outputs: list[str] = []

    print("[INFO] Starting gap analysis...", file=sys.stderr)

    try:
        for candidate in provider.stream_candidates():
            candidates_processed += 1
            print_progress(candidates_processed, "candidates analyzed")
            report = analyze_gaps(candidate)

            gap_count = sum(1 for e in report.entries if e.entry_type == "gap")
            gaps_detected += gap_count

            if args.format == "json":
                outputs.append(format_gap_report_json(report))
            else:
                outputs.append(format_gap_report_text(report))

    except DataFetchError as e:
        print(
            format_error(
                "Fetch Error",
                str(e),
                "Check the URL is accessible and returns valid JSON.",
            ),
            file=sys.stderr,
        )
        return 1
    except DataParseError as e:
        print(
            format_error(
                "Parse Error",
                str(e),
                "Verify the JSON structure matches the expected candidate format.",
            ),
            file=sys.stderr,
        )
        return 1

    separator = "\n\n" if args.format == "text" else ",\n"
    if args.format == "json":
        full_output = "[\n" + separator.join(outputs) + "\n]"
    else:
        full_output = separator.join(outputs)

    if args.output:
        args.output.write_text(full_output)
        print(f"Output written to: {args.output}")
    else:
        print(full_output)

    print(f"\n--- Summary ---", file=sys.stderr)
    print(f"Candidates processed: {candidates_processed}", file=sys.stderr)
    print(f"Employment gaps detected: {gaps_detected}", file=sys.stderr)

    return 0


def run_filter(args: argparse.Namespace) -> int:
    """Execute the filter command."""
    provider = UrlDataProvider(args.url)

    skills = tuple(s.strip() for s in args.skills.split(",") if s.strip())
    criteria = FilterCriteria(
        industry=args.industry,
        required_skills=skills,
        min_years_experience=args.min_years,
    )

    candidates_processed = 0
    candidates_matched = 0
    matched_list: list[Candidate] = []

    print("[INFO] Starting candidate filtering...", file=sys.stderr)

    try:
        for candidate in provider.stream_candidates():
            candidates_processed += 1
            print_progress(candidates_processed, "candidates processed")

            if matches_criteria(candidate, criteria):
                candidates_matched += 1
                matched_list.append(candidate)
                print(f"[MATCH] {candidate.name}")
            else:
                print(f"[SKIP]  {candidate.name}")

    except DataFetchError as e:
        print(
            format_error(
                "Fetch Error",
                str(e),
                "Check the URL is accessible and returns valid JSON.",
            ),
            file=sys.stderr,
        )
        return 1
    except DataParseError as e:
        print(
            format_error(
                "Parse Error",
                str(e),
                "Verify the JSON structure matches the expected candidate format.",
            ),
            file=sys.stderr,
        )
        return 1

    print("\n--- Summary ---", file=sys.stderr)
    print(f"Candidates processed: {candidates_processed}", file=sys.stderr)
    print(f"Candidates matched: {candidates_matched}", file=sys.stderr)
    print(f"Filter criteria:", file=sys.stderr)
    print(f"  Industry: {args.industry}", file=sys.stderr)
    print(f"  Skills: {', '.join(skills) if skills else '(none)'}", file=sys.stderr)
    print(f"  Min years: {args.min_years}", file=sys.stderr)

    if args.dry_run:
        print(f"\n[DRY RUN] No data was persisted.", file=sys.stderr)
    elif matched_list:
        try:
            repo = MongoRepository(args.db_uri, args.db_name)
            saved_count = repo.save_filtered_candidates(matched_list, criteria)
            print(f"\n[PERSISTED] {saved_count} candidates saved to MongoDB.", file=sys.stderr)
            print(f"  Database: {args.db_name}", file=sys.stderr)
            print(f"  Collection: filtered_candidates", file=sys.stderr)
        except RepositoryError as e:
            print(
                format_error(
                    "Database Error",
                    str(e),
                    "Verify MongoDB is running and the connection URI is correct.",
                ),
                file=sys.stderr,
            )
            return 1
    else:
        print(f"\n[INFO] No candidates matched - nothing to persist.", file=sys.stderr)

    return 0


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "analyze":
        return run_analyze(args)

    if args.command == "filter":
        return run_filter(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
