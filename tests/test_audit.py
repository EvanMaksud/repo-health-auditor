from pathlib import Path

from repo_health_auditor.audit import audit_repo


def test_repo_with_basics_gets_positive_score(tmp_path: Path):
    (tmp_path / "README.md").write_text(
        "# Demo\n\nInstall this project, use it from the command line, and run the test suite. "
        * 20,
        encoding="utf-8",
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "LICENSE").write_text("MIT\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    package = tmp_path / "demo"
    package.mkdir()
    (package / "app.py").write_text("print('hello')\n", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_app.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    report = audit_repo(tmp_path)

    assert report.score >= 70
    assert report.checks["readme"] is True
    assert report.checks["tests"] is True
    assert report.source_counts["Python"] == 2


def test_secret_pattern_is_reported(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Demo\n", encoding="utf-8")
    key_name = "API" + "_KEY"
    key_value = "abcdefghijkl" + "mnopqrstuvwxyz"
    (tmp_path / "app.py").write_text(f"{key_name} = '{key_value}'\n", encoding="utf-8")

    report = audit_repo(tmp_path)

    assert any(finding.code == "possible_secret" for finding in report.findings)
    assert report.score < 50
