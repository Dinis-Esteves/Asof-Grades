"""Grade rule.

K = rounding(best_fraction * total_quizzes)   # 0.7 * 25 -> 18 with ceil
n = quizzes published so far
n <= K: grade = mean of all n scores (no drops yet)
n >  K: grade = mean of the best K scores (worst n-K dropped)

Guaranteed = final grade if every remaining quiz scores 0:
sum of the best min(n, K) scores / K.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

ROUNDERS = {"ceil": math.ceil, "floor": math.floor, "round": lambda x: math.floor(x + 0.5)}


def counted_quizzes(total: int, fraction: float, rounding: str) -> int:
    return int(ROUNDERS[rounding](total * fraction))


@dataclass
class Student:
    student_id: str
    name: str = ""
    scores: list[float | None] = field(default_factory=list)  # one per published quiz
    grade: float = 0.0
    dropped: list[int] = field(default_factory=list)  # indices of dropped quizzes


def grade_student(scores: list[float], k: int) -> tuple[float, list[int]]:
    if not scores:
        return 0.0, []
    if len(scores) <= k:
        return sum(scores) / len(scores), []
    order = sorted(range(len(scores)), key=lambda i: scores[i])
    dropped = sorted(order[: len(scores) - k])
    kept = [s for i, s in enumerate(scores) if i not in dropped]
    return sum(kept) / k, dropped


def guaranteed_grade(scores: list[float], k: int) -> float:
    return sum(sorted(scores, reverse=True)[:k]) / k if k else 0.0
