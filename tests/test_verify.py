"""verify_csv tests — mocked HEAD/GET."""
from __future__ import annotations

import csv

import pytest

from osint_agent.verify import summarize, verify_csv

pytest_httpx = pytest.importorskip("pytest_httpx")


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "claim", "source_url", "source_type", "pub_date", "accessed_at",
                "extract", "identity_match_rationale", "corroboration", "caveats",
                "confidence", "notes",
            ],
        )
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def test_verify_marks_each_url(tmp_path, httpx_mock):
    csv_path = tmp_path / "ev.csv"
    _write_csv(
        csv_path,
        [
            {"claim": "ok url", "source_url": "https://ok.example/1", "confidence": "High"},
            {"claim": "bad url", "source_url": "https://bad.example/2", "confidence": "Low"},
        ],
    )
    httpx_mock.add_response(url="https://ok.example/1", method="HEAD", status_code=200)
    httpx_mock.add_response(url="https://bad.example/2", method="HEAD", status_code=404)

    rows = verify_csv(csv_path)
    assert len(rows) == 2
    assert rows[0].ok is True and rows[0].status == 200
    assert rows[1].ok is False and rows[1].status == 404

    s = summarize(rows)
    assert s == {"total": 2, "reachable": 1, "unreachable": 1}


def test_verify_handles_head_not_allowed_then_get(tmp_path, httpx_mock):
    csv_path = tmp_path / "ev.csv"
    _write_csv(
        csv_path,
        [{"claim": "ok", "source_url": "https://noop.example/x", "confidence": "Medium"}],
    )
    httpx_mock.add_response(
        url="https://noop.example/x", method="HEAD", status_code=405, text=""
    )
    httpx_mock.add_response(
        url="https://noop.example/x", method="GET", status_code=200, text="hi"
    )
    rows = verify_csv(csv_path)
    assert rows[0].ok is True
    assert rows[0].status == 200
