"""
Deadline Extractor — Parses uploaded syllabi and extracts structured deadlines
using Azure OpenAI, then stores them in the SQLite database.

Supports: .txt, .md, .pdf (via pypdf)
"""

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

from deadline_db import add_deadline

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Text Extraction
# ---------------------------------------------------------------------------

def extract_text_from_file(file_path: str) -> Tuple[str, str]:
    """
    Extract raw text from an uploaded file.

    Supports:
        .txt / .md  — read as UTF-8
        .pdf        — extract via pypdf (falls back to error message)

    Returns:
        (text, error_message) — error_message is empty string on success.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    if not path.exists():
        return "", f"File not found: {file_path}"

    # --- Plain text / Markdown ---
    if suffix in (".txt", ".md"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            return text, ""
        except Exception as e:
            return "", f"Error reading file: {e}"

    # --- PDF ---
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader          # type: ignore
        except ImportError:
            try:
                from PyPDF2 import PdfReader     # type: ignore  # older alias
            except ImportError:
                return (
                    "",
                    "PDF parsing requires 'pypdf'. "
                    "Run: pip install pypdf",
                )

        try:
            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text() or "")
            text = "\n".join(pages)
            return text, ""
        except Exception as e:
            return "", f"Error reading PDF: {e}"

    # --- Unsupported ---
    return (
        "",
        f"Unsupported file type '{suffix}'. "
        "Please upload a .txt, .md, or .pdf file.",
    )


# ---------------------------------------------------------------------------
# AI Extraction
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = """You are a precise academic deadline extractor.

Your ONLY job: extract real student deadlines (assignments, exams, quizzes, projects, essays, labs) from the provided syllabus text.

OUTPUT RULES — follow exactly:
1. Return a valid JSON array and NOTHING else — no markdown, no explanation.
2. Each element must have exactly three keys:
       "course"     : the course name or code (string)
       "assignment" : a concise name for the assignment/exam (string)
       "due_date"   : the deadline in YYYY-MM-DD format (string)
3. If the year is missing from the syllabus, infer it from context or use the current academic year.
4. IGNORE: lecture dates, office hours, reading assignments without a submission, holidays, general info.
5. If no real deadlines are found, return an empty JSON array: []

Example output:
[
  {"course": "CS 101", "assignment": "Homework 1", "due_date": "2025-09-15"},
  {"course": "CS 101", "assignment": "Midterm Exam", "due_date": "2025-10-20"}
]"""


async def extract_deadlines_with_ai(
    text: str,
    ai_client,
    max_text_chars: int = 12000,
) -> List[Dict[str, Any]]:
    """
    Send syllabus text to Azure OpenAI and parse the returned JSON.

    Args:
        text:           Syllabus text.
        ai_client:      AzureOpenAIClient instance.
        max_text_chars: Truncate input to avoid token limits.

    Returns:
        List of dicts with keys: course, assignment, due_date.
    """
    # Truncate very long documents
    if len(text) > max_text_chars:
        text = text[:max_text_chars] + "\n\n[... document truncated ...]"

    user_prompt = (
        "Extract all academic deadlines from the syllabus below.\n\n"
        "---SYLLABUS START---\n"
        f"{text}\n"
        "---SYLLABUS END---\n\n"
        "Return ONLY a JSON array as described."
    )

    # We send this as a standalone call without conversation history
    # to get a clean, structured response.
    try:
        raw_response = await ai_client.client.chat.completions.create(
            model=ai_client.deployment,
            messages=[
                {"role": "system", "content": _EXTRACTION_SYSTEM_PROMPT},
                {"role": "user",   "content": user_prompt},
            ],
            max_completion_tokens=1500,
        )
        raw_text = raw_response.choices[0].message.content or ""
        logger.info(f"Raw AI extraction response: {raw_text[:300]}")
    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return []

    # --- Parse JSON ---
    # Strip potential markdown fences the model may add despite instructions
    clean = re.sub(r"```(?:json)?", "", raw_text).strip().strip("`").strip()

    # Find the JSON array boundaries
    start = clean.find("[")
    end   = clean.rfind("]")
    if start == -1 or end == -1:
        logger.warning("No JSON array found in AI response.")
        return []

    try:
        deadlines = json.loads(clean[start : end + 1])
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}\nRaw: {clean}")
        return []

    # Validate each entry
    validated = []
    for item in deadlines:
        if not isinstance(item, dict):
            continue
        course     = str(item.get("course", "")).strip()
        assignment = str(item.get("assignment", "")).strip()
        due_date   = str(item.get("due_date", "")).strip()

        if not (course and assignment and due_date):
            logger.debug(f"Skipping incomplete entry: {item}")
            continue

        # Basic date format check: YYYY-MM-DD
        if not re.match(r"\d{4}-\d{2}-\d{2}", due_date):
            logger.debug(f"Skipping bad date format '{due_date}': {item}")
            continue

        validated.append(
            {"course": course, "assignment": assignment, "due_date": due_date}
        )

    logger.info(f"✅ Extracted {len(validated)} valid deadline(s)")
    return validated


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def process_uploaded_file(
    file_path: str,
    ai_client,
) -> Tuple[int, int, str]:
    """
    Full pipeline: extract text → call AI → save to DB.

    Args:
        file_path:  Path to the uploaded file.
        ai_client:  AzureOpenAIClient instance.

    Returns:
        (inserted_count, skipped_count, status_message)
    """
    filename = Path(file_path).name

    # 1. Extract text
    text, error = extract_text_from_file(file_path)
    if error:
        return 0, 0, f"❌ {error}"
    if not text.strip():
        return 0, 0, f"❌ No readable text found in '{filename}'."

    logger.info(f"Extracted {len(text)} chars from '{filename}'")

    # 2. AI extraction
    deadlines = await extract_deadlines_with_ai(text, ai_client)
    if not deadlines:
        return (
            0, 0,
            f"⚠️ No academic deadlines detected in '{filename}'. "
            "The AI found only lecture dates or general info.",
        )

    # 3. Insert into DB (deduplication handled inside add_deadline)
    inserted = 0
    skipped  = 0
    for d in deadlines:
        added = add_deadline(
            course=d["course"],
            assignment=d["assignment"],
            due_date=d["due_date"],
            source_file=filename,
        )
        if added:
            inserted += 1
        else:
            skipped += 1

    status = (
        f"✅ Processed **{filename}**\n"
        f"- Found {len(deadlines)} deadline(s)\n"
        f"- Added {inserted} new | Skipped {skipped} duplicate(s)"
    )
    logger.info(status)
    return inserted, skipped, status
