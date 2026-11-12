"""Render the static site (single self-contained index.html)."""

from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="pt">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ASof Quiz Grades</title>
<style>
:root {{ --bg:#fff; --fg:#1b1b1f; --muted:#6b6b76; --line:#e4e4ea; --accent:#2457d6; --drop:#b0b0b8; --row:#f6f7fb; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#121216; --fg:#ececf1; --muted:#9a9aa6; --line:#2a2a33; --accent:#7aa2ff; --drop:#55555f; --row:#1a1a20; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif; }}
main {{ max-width:1100px; margin:0 auto; padding:24px 16px 48px; }}
h1 {{ margin:0 0 4px; font-size:1.5rem; }}
.meta {{ color:var(--muted); margin-bottom:16px; }}
.hint {{ color:var(--muted); font-size:.85rem; margin:0 0 8px; }}
input {{ width:100%; max-width:360px; padding:8px 10px; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--fg); font:inherit; margin-bottom:12px; }}
.wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:8px; }}
table {{ border-collapse:collapse; width:100%; font-variant-numeric:tabular-nums; }}
th, td {{ padding:6px 10px; border-bottom:1px solid var(--line); text-align:center; white-space:nowrap; }}
th {{ position:sticky; top:0; background:var(--bg); cursor:pointer; user-select:none; font-weight:600; }}
th:hover {{ color:var(--accent); }}
th .arrow {{ display:inline-block; width:1em; margin-left:4px; color:var(--muted); opacity:.45; }}
th[aria-sort] .arrow {{ color:var(--accent); opacity:1; }}
th.l, td.l {{ text-align:left; width:1%; padding-right:24px; }}
tbody tr:nth-child(even) {{ background:var(--row); }}
td.grade {{ font-weight:700; color:var(--accent); }}
td.drop {{ color:var(--drop); text-decoration:line-through; }}
td.miss {{ color:var(--muted); }}
</style>
</head>
<body>
<main>
<h1>ASof quiz grades</h1>
<div class="meta">{n} of {total} quizzes published · best {k} count · updated {updated}</div>
<input id="q" type="search" placeholder="Filter by student number" autocomplete="off">
<p class="hint">Click a column header to sort by it; click again to reverse. ▲ ascending, ▼ descending.</p>
<div class="wrap"><table id="t"><thead></thead><tbody></tbody></table></div>
</main>
<script>
const D = {data};
const head = ["Number", "Current", "Final", ...D.quizzes.map((q, i) => "Q" + (i + 1))];
const Q0 = 3; // first quiz column
const thead = document.querySelector("#t thead"), tbody = document.querySelector("#t tbody");
let sortCol = 1, asc = false;
const info = i => i >= Q0 ? D.quizzes[i - Q0] + ". " : i === 2 ? "Final grade if every remaining quiz scores 0. " : "";
thead.innerHTML = "<tr>" + head.map((h, i) => `<th class="${{i === 0 ? "l" : ""}}" title="${{info(i)}}Click to sort, click again to reverse">${{h}}<span class="arrow"></span></th>`).join("") + "</tr>";
const ths = [...thead.querySelectorAll("th")];
ths.forEach((th, i) => th.onclick = () => {{ asc = sortCol === i ? !asc : i === 0; sortCol = i; render(); }});
function showSort() {{
  ths.forEach((th, i) => {{
    const on = i === sortCol;
    th.querySelector(".arrow").textContent = on ? (asc ? "▲" : "▼") : "↕";
    if (on) th.setAttribute("aria-sort", asc ? "ascending" : "descending"); else th.removeAttribute("aria-sort");
  }});
}}
const key = (s, i) => i === 0 ? s.id : i === 1 ? s.grade : i === 2 ? s.guaranteed : (s.scores[i - Q0] ?? -1);
const fmt = x => x == null ? "–" : (+x.toFixed(2)).toString();
function render() {{
  showSort();
  const q = document.getElementById("q").value.trim().toLowerCase();
  const rows = D.students.filter(s => !q || s.id.includes(q))
    .sort((a, b) => {{ const x = key(a, sortCol), y = key(b, sortCol); return (x < y ? -1 : x > y ? 1 : 0) * (asc ? 1 : -1); }});
  tbody.innerHTML = rows.map(s => "<tr>" +
    `<td class="l">${{s.id}}</td><td class="grade">${{fmt(s.grade)}}</td><td>${{fmt(s.guaranteed)}}</td>` +
    s.scores.map((v, i) => `<td class="${{s.dropped.includes(i) ? "drop" : v == null ? "miss" : ""}}">${{fmt(v)}}</td>`).join("") +
    "</tr>").join("");
}}
document.getElementById("q").oninput = render;
render();
</script>
</body>
</html>
"""


def write_site(out_dir: Path, quizzes: list[str], students: list[dict], total: int, k: int) -> Path:
    n = len(quizzes)
    data = {
        "quizzes": [html.escape(q) for q in quizzes],
        "students": students,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    page = TEMPLATE.format(
        n=n, total=total, k=k,
        updated=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        data=json.dumps(data, ensure_ascii=False).replace("</", "<\\/"),
    )
    path = out_dir / "index.html"
    path.write_text(page, encoding="utf-8")
    return path
