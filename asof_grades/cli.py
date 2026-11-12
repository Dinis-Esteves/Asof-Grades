"""asof-grades: fetch quiz PDFs from Fénix, compute grades, build docs/index.html."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

from .build import write_site
from .compute import Student, counted_quizzes, grade_student
from .fetch import download, list_quiz_pdfs, load_cookie, session_with_cookie
from .parse import parse_pdf

ROOT = Path(__file__).resolve().parent.parent


def _natural(p: Path) -> list:
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true", help="skip Fénix; use PDFs already in data/pdfs/")
    ap.add_argument("--config", type=Path, default=ROOT / "config.toml")
    args = ap.parse_args()

    cfg = tomllib.loads(args.config.read_text())
    pdf_dir = ROOT / "data" / "pdfs"

    if args.offline:
        pdfs = [(p.stem, p) for p in sorted(pdf_dir.glob("*.pdf"), key=_natural)]
    else:
        session = session_with_cookie(load_cookie(ROOT / ".env"))
        links = list_quiz_pdfs(session, cfg["grades_url"])
        print(f"Found {len(links)} PDF link(s) on Fénix.")
        pdfs = [(link.title, path) for link, path in download(session, links, pdf_dir)]

    if not pdfs:
        raise SystemExit("No quiz PDFs found.")

    students: dict[str, Student] = {}
    quizzes: list[str] = []
    for qi, (title, path) in enumerate(pdfs):
        rows = parse_pdf(path)
        print(f"  {path.name}: {len(rows)} student(s)")
        quizzes.append(title)
        for r in rows:
            s = students.setdefault(r.student_id, Student(r.student_id))
            s.name = s.name or r.name
            s.scores += [None] * (qi - len(s.scores))
            s.scores.append(r.score)
    for s in students.values():
        s.scores += [None] * (len(quizzes) - len(s.scores))

    k = counted_quizzes(cfg["total_quizzes"], cfg["best_fraction"], cfg["rounding"])
    missing = cfg.get("missing_score", 0)
    out = []
    for s in students.values():
        s.grade, s.dropped = grade_student([missing if v is None else v for v in s.scores], k)
        out.append({"id": s.student_id, "name": s.name, "grade": s.grade, "dropped": s.dropped, "scores": s.scores})

    path = write_site(ROOT / "docs", quizzes, out, cfg["total_quizzes"], k, cfg["max_score"])
    print(f"Wrote {path.relative_to(ROOT)} ({len(out)} students, {len(quizzes)} quizzes, best {k} count).")


if __name__ == "__main__":
    main()
