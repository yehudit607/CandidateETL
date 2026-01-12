"""Report generation service for gap analysis output."""

import json
from typing import Any

from src.domain.models import GapReport


def format_gap_report_text(report: GapReport) -> str:
    lines = [f"Hello {report.candidate_name},"]

    if not report.entries:
        lines.append("No work history recorded.")
    else:
        for entry in report.entries:
            lines.append(entry.content)

    return "\n".join(lines)


def format_gap_report_json(report: GapReport) -> str:
    data: dict[str, Any] = {
        "candidate_name": report.candidate_name,
        "entries": [
            {
                "entry_type": entry.entry_type,
                "content": entry.content,
                "gap_days": entry.gap_days,
            }
            for entry in report.entries
        ],
    }
    return json.dumps(data, indent=2)
