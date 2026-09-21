from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

SOURCE_EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".jsx": "JavaScript",
    ".html": "HTML",
    ".css": "CSS",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".c": "C",
}

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".env",
    ".md",
    ".txt",
    ".ps1",
    ".bat",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    path: str = ""


@dataclass
class RepoReport:
    root: Path
    score: int
    files_scanned: int
    source_counts: dict[str, int]
    checks: dict[str, bool]
    findings: list[Finding] = field(default_factory=list)


def audit_repo(root: str | Path) -> RepoReport:
    repo_root = Path(root).resolve()
    if not repo_root.exists():
        raise FileNotFoundError(f"Repository does not exist: {repo_root}")

    files = [path for path in repo_root.rglob("*") if path.is_file() and ".git" not in path.parts]
    source_counts = count_sources(files)
    checks = {
        "readme": has_file(repo_root, ["README.md", "readme.md", "README.rst"]),
        "license": has_prefix(repo_root, "LICENSE"),
        "tests": has_tests(repo_root),
        "packaging": has_file(repo_root, ["pyproject.toml", "package.json", "requirements.txt", "setup.py"]),
        "ci": (repo_root / ".github" / "workflows").exists(),
        "gitignore": (repo_root / ".gitignore").exists(),
        "source_files": bool(source_counts),
    }

    findings: list[Finding] = []
    evaluate_readme(repo_root, checks["readme"], findings)
    evaluate_tests(repo_root, checks["tests"], findings)
    evaluate_missing_basics(checks, findings)
    scan_for_secrets(repo_root, files, findings)

    score = calculate_score(checks, findings)
    return RepoReport(
        root=repo_root,
        score=score,
        files_scanned=len(files),
        source_counts=dict(source_counts),
        checks=checks,
        findings=findings,
    )


def count_sources(files: list[Path]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for path in files:
        language = SOURCE_EXTENSIONS.get(path.suffix.lower())
        if language:
            counts[language] += 1
    return counts


def has_file(root: Path, names: list[str]) -> bool:
    return any((root / name).exists() for name in names)


def has_prefix(root: Path, prefix: str) -> bool:
    return any(path.name.upper().startswith(prefix) for path in root.iterdir() if path.is_file())


def has_tests(root: Path) -> bool:
    test_dir = root / "tests"
    if test_dir.exists() and any(test_dir.rglob("test_*.py")):
        return True
    return any(path.name.startswith("test_") and path.suffix == ".py" for path in root.rglob("*.py"))


def evaluate_readme(root: Path, has_readme: bool, findings: list[Finding]) -> None:
    if not has_readme:
        findings.append(Finding("error", "missing_readme", "Repository has no README."))
        return

    readme = next(path for path in root.iterdir() if path.name.lower().startswith("readme"))
    text = readme.read_text(encoding="utf-8", errors="replace")
    lower = text.lower()
    if len(text.split()) < 120:
        findings.append(
            Finding("warning", "thin_readme", "README is short; add usage, install, and examples.", readme.name)
        )
    for keyword in ("install", "usage", "test"):
        if keyword not in lower:
            findings.append(
                Finding("info", f"readme_missing_{keyword}", f"README does not mention {keyword}.", readme.name)
            )


def evaluate_tests(root: Path, has_test_files: bool, findings: list[Finding]) -> None:
    if not has_test_files:
        findings.append(Finding("warning", "missing_tests", "No test files were found."))
        return

    test_files = list(root.rglob("test_*.py"))
    if len(test_files) < 2:
        findings.append(Finding("info", "low_test_count", "Only one test file was found."))


def evaluate_missing_basics(checks: dict[str, bool], findings: list[Finding]) -> None:
    if not checks["license"]:
        findings.append(Finding("info", "missing_license", "No license file was found."))
    if not checks["packaging"]:
        findings.append(Finding("warning", "missing_packaging", "No packaging or dependency file was found."))
    if not checks["ci"]:
        findings.append(Finding("info", "missing_ci", "No GitHub Actions workflow was found."))
    if not checks["gitignore"]:
        findings.append(Finding("info", "missing_gitignore", "No .gitignore file was found."))
    if not checks["source_files"]:
        findings.append(Finding("warning", "missing_source", "No source files were detected."))


def scan_for_secrets(root: Path, files: list[Path], findings: list[Finding]) -> None:
    for path in files:
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        if path.stat().st_size > 512_000:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(
                    Finding(
                        "error",
                        "possible_secret",
                        "Possible hard-coded secret found. Review before publishing.",
                        str(path.relative_to(root)),
                    )
                )
                break


def calculate_score(checks: dict[str, bool], findings: list[Finding]) -> int:
    score = 0
    score += 20 if checks["readme"] else 0
    score += 15 if checks["tests"] else 0
    score += 15 if checks["packaging"] else 0
    score += 10 if checks["ci"] else 0
    score += 10 if checks["license"] else 0
    score += 10 if checks["gitignore"] else 0
    score += 20 if checks["source_files"] else 0

    penalties = {"error": 12, "warning": 5, "info": 1}
    for finding in findings:
        score -= penalties.get(finding.severity, 1)
    return max(0, min(100, score))

