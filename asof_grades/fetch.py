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
        raise SystemExit("Set FENIX_USERNAME and FENIX_PASSWORD secrets (or FENIX_COOKIE).")
    if not cookie:
        cookie = getpass.getpass("Fénix Cookie header (hidden): ").strip()
    if not cookie:
        raise SystemExit("No Fénix cookie provided.")
    return cookie


def read_env(env_file: Path, key: str) -> str | None:
    """Value of `key` from the environment, else from .env."""
    if value := os.environ.get(key):
        return value
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() == key:
                return v.strip().strip('"').strip("'") or None
    return None


def session_with_login(username: str, password: str, page_url: str) -> requests.Session:
    """Log in through IST CAS (id.tecnico.ulisboa.pt) and return a session holding Fénix cookies."""
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    login_url = f"https://fenix.tecnico.ulisboa.pt/login?callback={page_url}"
    resp = s.get(login_url, timeout=30)
    resp.raise_for_status()

    form = BeautifulSoup(resp.text, "html.parser").find("form", id="credential")
    if form is None:
        raise SystemExit(f"CAS login form not found at {urlparse(resp.url).netloc}.")
    data = {i["name"]: i.get("value", "") for i in form.find_all("input") if i.get("name")}
    data.update(username=username, password=password)

    resp = s.post(urljoin(resp.url, form["action"]), data=data, timeout=30)
    resp.raise_for_status()
    host = urlparse(resp.url).netloc
    if host != "fenix.tecnico.ulisboa.pt":
        err = BeautifulSoup(resp.text, "html.parser").select_one(".error-message, #msg, .errors, .alert")
        reason = " ".join(err.get_text(" ", strip=True).split()) if err else "no error message"
        raise SystemExit(f"Fénix login failed (stopped at {host}): {reason}")
    print("Logged in to Fénix.")
    return s


def session_with_cookie(cookie: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({"Cookie": cookie, "User-Agent": USER_AGENT})
    return s


def list_quiz_pdfs(session: requests.Session, page_url: str) -> list[QuizLink]:
    resp = session.get(page_url, timeout=30)
    redirected_to_login = "/login" in urlparse(resp.url).path
    header = session.headers.get("Cookie", "")
    names = sorted({c.split("=", 1)[0].strip() for c in header.split(";") if "=" in c} | set(session.cookies.keys()))
    print(f"Fénix: HTTP {resp.status_code}, final path {urlparse(resp.url).path}, cookie names sent {names}")
    if resp.status_code == 401 or redirected_to_login:
        raise SystemExit(
            "Fénix rejected the cookie (expired, incomplete, or bound to another IP). "
            "Refresh FENIX_COOKIE or set FENIX_USERNAME/FENIX_PASSWORD."
        )
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
