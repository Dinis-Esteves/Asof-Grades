"""Download quiz PDFs from the Fénix grades page using a session cookie."""

from __future__ import annotations

import getpass
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "asof-grades/0.1"


@dataclass(frozen=True)
class QuizLink:
    title: str
    url: str


def load_cookie(env_file: Path) -> str:
    """Read FENIX_COOKIE from the environment, then .env, then prompt (hidden input)."""
    cookie = os.environ.get("FENIX_COOKIE")
    if not cookie and env_file.exists():
        for line in env_file.read_text().splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "FENIX_COOKIE":
                cookie = value.strip().strip('"').strip("'")
                break
    if not cookie and os.environ.get("CI"):
        raise SystemExit("FENIX_COOKIE secret is not set.")
    if not cookie:
        cookie = getpass.getpass("Fénix Cookie header (hidden): ").strip()
    if not cookie:
        raise SystemExit("No Fénix cookie provided.")
    return cookie


def session_with_cookie(cookie: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Cookie": cookie, "User-Agent": USER_AGENT})
    return s


def list_quiz_pdfs(session: requests.Session, page_url: str) -> list[QuizLink]:
    resp = session.get(page_url, timeout=30)
    if resp.status_code == 401 or "/login?callback=" in resp.text:
        raise SystemExit("Fénix rejected the cookie (expired?). Refresh FENIX_COOKIE in .env.")
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    links: list[QuizLink] = []
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        url = urljoin(page_url, a["href"])
        path = unquote(urlparse(url).path).lower()
        if not (path.endswith(".pdf") or "/downloadfile/" in path):
            continue
        if url in seen:
            continue
        seen.add(url)
        title = " ".join(a.get_text(" ", strip=True).split()) or Path(path).stem
        links.append(QuizLink(title=title, url=url))
    return links


def _safe_name(title: str, url: str) -> str:
    base = re.sub(r"[^\w.-]+", "_", title).strip("_") or Path(urlparse(url).path).stem
    return base if base.lower().endswith(".pdf") else base + ".pdf"


def download(session: requests.Session, links: list[QuizLink], out_dir: Path) -> list[tuple[QuizLink, Path]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for link in links:
        dest = out_dir / _safe_name(link.title, link.url)
        if not dest.exists():
            resp = session.get(link.url, timeout=60)
            resp.raise_for_status()
            if not resp.content.startswith(b"%PDF"):
                print(f"  skip (not a PDF): {link.title}")
                continue
            dest.write_bytes(resp.content)
            print(f"  downloaded {dest.name}")
        result.append((link, dest))
    return result
