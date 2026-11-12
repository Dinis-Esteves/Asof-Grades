# ASof quiz grades

Fetches every quiz PDF from the Fénix grades page, merges them, and builds a static page (`docs/index.html`) with each student's current grade.

## Grade rule

- 25 quizzes total (weeks 9–15: 4/week, except 3 weeks with 3: week 10 + 2 more).
- Best 70% count: `0.7 × 25 = 17.5` → 18 (`rounding` in `config.toml`).
- Until more than 18 quizzes are published: grade = mean of all published quizzes.
- After that: grade = mean of the best 18; dropped quizzes are struck through.
- Absent from a quiz PDF = `missing_score` (0).

## Automatic updates (GitHub Actions)

`.github/workflows/update.yml` runs Tue–Fri at 15:00 (Lisbon), on push to `main`, and on demand. It downloads new PDFs, builds the site and deploys it to GitHub Pages. Grades are never committed to the repo; they only exist in the deployed site.

Setup:

1. Settings → Secrets and variables → Actions → New repository secrets: `FENIX_USERNAME` (Técnico ID, e.g. `ist1xxxxxx`) and `FENIX_PASSWORD`. Each run logs in through id.tecnico.ulisboa.pt. `FENIX_COOKIE` still works as a fallback when these are unset.
2. Settings → Pages → Source: **GitHub Actions**.
3. Actions → Update grades → Run workflow.

A failed login stops the run with the reason from the login page and GitHub emails you.

## Local usage

```sh
cp .env.example .env   # fill in username/password (or cookie); .env is gitignored
uv run asof-grades     # downloads new PDFs to data/pdfs/, writes docs/index.html
uv run asof-grades --offline   # rebuild from PDFs already downloaded
```

No credentials? The script prompts for the cookie with hidden input.
