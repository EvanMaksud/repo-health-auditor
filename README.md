# Repo Health Auditor

A small CLI that audits whether a repository is ready to show publicly.

It checks the things recruiters, collaborators, and future maintainers usually notice first: README quality, project structure, tests, dependency files, CI configuration, license, and obvious secret-leak patterns.

## Features

- Scores a repository out of 100.
- Detects README, license, tests, package metadata, CI workflows, and `.gitignore`.
- Counts source files by language extension.
- Scans text files for common accidental secret patterns.
- Produces Markdown or JSON reports.
- Uses only the Python standard library.

## Install

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## Usage

```powershell
repo-health "path\to\repository" --output repo-health-report.md
```

JSON output:

```powershell
repo-health "path\to\repository" --format json --output repo-health-report.json
```

Run without installing:

```powershell
python -m repo_health_auditor "path\to\repository"
```

## What It Checks

| Area | Examples |
| --- | --- |
| Documentation | README exists, README has enough substance, usage/install/test sections |
| Testing | `tests/` directory, test files, pytest/unittest hints |
| Packaging | `pyproject.toml`, `package.json`, `requirements.txt`, lockfiles |
| Automation | GitHub Actions workflow files |
| Hygiene | `.gitignore`, license, source layout |
| Security | Suspicious API key/token/password assignments |

## Test

```powershell
python -m pytest -q
```

## Why This Project Exists

A good GitHub profile is not only about code volume. It is about whether a stranger can understand, run, and trust a project. This tool helps make that review process concrete.

