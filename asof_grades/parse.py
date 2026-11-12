"""Extract (student id, name, score) rows from a quiz PDF.

Generic heuristic until the real PDF layout is known: each row needs a student
number (e.g. 'ist1234567' or '123456') and a numeric score (last number on the row,
',' or '.' decimals). Everything between is treated as the name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

ID_RE = re.compile(r"\b(ist\d{5,8}|\d{5,8})\b", re.IGNORECASE)
NUM_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:[.,]\d+)?)(?![\w.,])")


@dataclass(frozen=True)
class Row:
    student_id: str
    name: str
    score: float | None  # None = present in PDF but no numeric grade (e.g. "F", "NA")


def _parse_line(cells: list[str]) -> Row | None:
    line = " ".join(c for c in cells if c)
    m = ID_RE.search(line)
    if not m:
        return None
    student_id = m.group(1).lower()
    rest = line[m.end():]
    nums = list(NUM_RE.finditer(rest))
    score = float(nums[-1].group(1).replace(",", ".")) if nums else None
    name_part = rest[: nums[-1].start()] if nums else rest
    name = " ".join(re.sub(r"[^\w\s'.-]", " ", name_part).split())
    return Row(student_id=student_id, name=name, score=score)


def parse_pdf(path: Path) -> list[Row]:
    rows: dict[str, Row] = {}
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            lines: list[list[str]] = [
                [c or "" for c in r] for t in tables for r in t
            ] or [[ln] for ln in (page.extract_text() or "").splitlines()]
            for cells in lines:
                row = _parse_line(cells)
                if row and row.student_id not in rows:
                    rows[row.student_id] = row
    return list(rows.values())
