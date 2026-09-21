from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import RepoReport, audit_repo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a repository for public portfolio readiness.")
    parser.add_argument("repository", help="Path to the repository.")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", "-o", help="Write the report to a file.")
    args = parser.parse_args(argv)

    report = audit_repo(args.repository)
    body = render_json(report) if args.format == "json" else render_markdown(report)

    if args.output:
        Path(args.output).write_text(body, encoding="utf-8")
    else:
        print(body)

    return 1 if any(finding.severity == "error" for finding in report.findings) else 0


def render_json(report: RepoReport) -> str:
    payload = {
        "root": str(report.root),
        "score": report.score,
        "files_scanned": report.files_scanned,
        "source_counts": report.source_counts,
        "checks": report.checks,
        "findings": [finding.__dict__ for finding in report.findings],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def render_markdown(report: RepoReport) -> str:
    lines = [
        "# Repository Health Report",
        "",
        f"Repository: `{report.root}`",
        "",
        "## Summary",
        "",
        f"- Score: **{report.score}/100**",
        f"- Files scanned: **{report.files_scanned}**",
        "",
        "## Checks",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    for name, passed in report.checks.items():
        lines.append(f"| {name.replace('_', ' ').title()} | {'pass' if passed else 'missing'} |")

    lines.extend(["", "## Source Files", "", "| Language | Files |", "| --- | ---: |"])
    if report.source_counts:
        for language, count in sorted(report.source_counts.items()):
            lines.append(f"| {language} | {count} |")
    else:
        lines.append("| None detected | 0 |")

    lines.extend(["", "## Findings", ""])
    if not report.findings:
        lines.append("No findings. Nice.")
    else:
        lines.extend(["| Severity | Code | Path | Message |", "| --- | --- | --- | --- |"])
        for finding in report.findings:
            lines.append(
                f"| {finding.severity} | `{finding.code}` | `{finding.path}` | {finding.message} |"
            )

    return "\n".join(lines) + "\n"

