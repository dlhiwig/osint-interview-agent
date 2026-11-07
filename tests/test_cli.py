"""CLI tests using typer's CliRunner."""
from __future__ import annotations

import csv

from typer.testing import CliRunner

from osint_agent.cli import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip()


def test_dry_run_lists_tools():
    result = runner.invoke(app, ["research", "Test Subject", "--dry-run"])
    assert result.exit_code == 0
    assert "Tool availability" in result.stdout
    # One of the always-on tools should be enabled
    assert "screen_opensanctions" in result.stdout


def test_research_without_authorization_exits_2():
    result = runner.invoke(app, ["research", "Test Subject"])
    assert result.exit_code == 2
    assert "authorization" in result.stdout.lower()


def test_verify_against_mocked_csv(tmp_path, monkeypatch):
    csv_path = tmp_path / "ev.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "claim", "source_url", "source_type", "pub_date", "accessed_at",
                "extract", "identity_match_rationale", "corroboration", "caveats",
                "confidence", "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {"claim": "x", "source_url": "https://ok.example/1", "confidence": "High"}
        )

    # Stub head_ok to avoid real network; CLI imports verify.verify_csv which uses _http.head_ok
    import osint_agent.verify as verify_module

    monkeypatch.setattr(
        verify_module, "head_ok", lambda url, timeout=15.0: (True, 200)
    )
    result = runner.invoke(app, ["verify", str(csv_path)])
    assert result.exit_code == 0
    assert "Reachable" in result.stdout
    assert "https://ok.example/1" in result.stdout
