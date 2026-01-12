"""Data transformer for converting HiredScore API format to our format."""

import json
from datetime import datetime
from typing import Any


def transform_hiredscore_to_standard(hiredscore_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Transform HiredScore API format to our standard format.

    HiredScore format: List of candidate objects with 'experience', 'extracted_skills', etc.
    Our format: {"candidates": [{"name": str, "skills": [str], "jobs": [job_obj]}]}
    """
    candidates = []

    for idx, candidate_data in enumerate(hiredscore_data):
        # Extract name from contact_info or generate from index
        name = _extract_name(candidate_data, idx)

        # Extract skills
        skills = _extract_skills(candidate_data)

        # Extract and transform jobs
        jobs = _extract_jobs(candidate_data)

        candidates.append({
            "name": name,
            "skills": skills,
            "jobs": jobs
        })

    return {"candidates": candidates}


def _extract_name(data: dict[str, Any], index: int) -> str:
    """Extract candidate name from contact_info or generate placeholder."""
    contact_info = data.get("contact_info", {})

    # Try to get name from contact_info
    if isinstance(contact_info, dict):
        name_field = contact_info.get("name", {})

        # Handle case where name is a dict with formatted_name
        if isinstance(name_field, dict):
            formatted_name = name_field.get("formatted_name", "")
            if formatted_name:
                return formatted_name
            # Try to construct from given_name and family_name
            given_name = name_field.get("given_name", "")
            family_name = name_field.get("family_name", "")
            if given_name or family_name:
                return f"{given_name} {family_name}".strip()

        # Handle case where name is a string
        if isinstance(name_field, str) and name_field:
            return name_field

        # Fallback to first_name/last_name fields
        first_name = contact_info.get("first_name", "")
        last_name = contact_info.get("last_name", "")
        if first_name or last_name:
            return f"{first_name} {last_name}".strip()

    # Fallback to candidate index
    return f"Candidate {index + 1}"


def _extract_skills(data: dict[str, Any]) -> list[str]:
    """Extract skills from extracted_skills or resume_skills."""
    skills = []

    # Try extracted_skills first
    extracted_skills = data.get("extracted_skills", [])
    if isinstance(extracted_skills, list):
        for skill in extracted_skills:
            if isinstance(skill, dict):
                skill_name = skill.get("skill_name", "")
                if skill_name:
                    skills.append(skill_name)
            elif isinstance(skill, str):
                skills.append(skill)

    # Fallback to resume_skills
    if not skills:
        resume_skills = data.get("resume_skills", [])
        if isinstance(resume_skills, list):
            skills = [s for s in resume_skills if isinstance(s, str)]

    return skills


def _extract_jobs(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract and transform jobs from experience array."""
    jobs = []
    experience = data.get("experience", [])

    if not isinstance(experience, list):
        return jobs

    for exp in experience:
        if not isinstance(exp, dict):
            continue

        # Extract job fields
        title = exp.get("title", "")
        company_name = exp.get("company_name", "")

        # Extract industry from company_details
        industry = "Unknown"
        company_details = exp.get("company_details")
        if isinstance(company_details, dict):
            industry = company_details.get("industry", "Unknown")

        # Extract location
        location = "Unknown"
        location_data = exp.get("location")
        if isinstance(location_data, dict):
            location = location_data.get("short_display_address", "Unknown")

        # Extract dates (already in format like "Jan/01/2008")
        start_date = exp.get("start_date")
        end_date = exp.get("end_date")  # None for current jobs

        # Convert HiredScore date format to ISO format
        start_date_iso = _convert_date_to_iso(start_date) if start_date else None
        end_date_iso = _convert_date_to_iso(end_date) if end_date else None

        # Skip if missing required fields
        if not title or not company_name or not start_date_iso:
            continue

        jobs.append({
            "title": title,
            "company": company_name,
            "industry": industry,
            "location": location,
            "start_date": start_date_iso,
            "end_date": end_date_iso
        })

    return jobs


def _convert_date_to_iso(date_str: str) -> str | None:
    """Convert HiredScore date format (Jan/01/2008) to ISO format (2008-01-01)."""
    if not date_str:
        return None

    try:
        # Parse format like "Jan/01/2008"
        dt = datetime.strptime(date_str, "%b/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return None


def load_and_transform_hiredscore_json(json_content: str) -> dict[str, Any]:
    """Load HiredScore JSON and transform to standard format."""
    data = json.loads(json_content)

    # If it's already in standard format, return as-is
    if isinstance(data, dict) and "candidates" in data:
        return data

    # If it's HiredScore format (list), transform it
    if isinstance(data, list):
        return transform_hiredscore_to_standard(data)

    raise ValueError("Unknown JSON format")
