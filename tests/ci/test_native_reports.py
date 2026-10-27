# SPDX-License-Identifier: Apache-2.0
"""Native CI rendering preserves retained evidence and fails closed."""

import json
from pathlib import Path

import pytest
from ci.native_reports import render_native_reports
from ci.run_tier1 import _summary

from skillevaluator.models import Finding, ValidationResult
from skillevaluator.reporting.json_reporter import JSONReporter
from skillevaluator.reporting.retained import RetainedReportError


def _write_fixture(tmp_path: Path, failed=False):
    result = ValidationResult(validator_name="Schema", validator_description="Validate skill metadata")
    if failed:
        result.add_finding(
            Finding(
                category="SCHEMA",
                severity="high",
                check_name="name",
                message="Bad name </script><img src=x onerror=alert(1)>",
                file_path="/workspace/skills/example/SKILL.md",
                suggestion="Use kebab-case",
            )
        )
    payload = json.loads(JSONReporter(include_timestamp=False).render_all([result]))
    directory = tmp_path / "skill-001"
    directory.mkdir()
    raw = json.dumps(payload, indent=3) + "\n"
    (directory / "skillevaluator-tier1.json").write_text(raw)
    (directory / "skillevaluator-tier1.html").write_text('<script>alert("ARTIFACT HTML")</script>')
    row = {
        "path": "skills/example",
        "report_dir": "skill-001",
        "exit_code": 1 if failed else 0,
        "passed": not failed,
        **{
            key: payload[key]
            for key in (
                "overall_status",
                "incomplete_scans",
                "total_validators",
                "total_errors",
                "total_warnings",
                "severity_counts",
            )
        },
    }
    return _summary([row]), raw


@pytest.mark.parametrize("failed", [False, True])
def test_native_reports_overwrite_artifact_html_keep_json_and_link_details(tmp_path, failed):
    summary, raw = _write_fixture(tmp_path, failed)
    render_native_reports(tmp_path, summary, {"report_url": "https://example.com/run", "llm_enabled": False})
    native = (tmp_path / "skill-001/skillevaluator-tier1.html").read_text()
    index = (tmp_path / "index.html").read_text()
    assert "ARTIFACT HTML" not in native
    assert 'href="../index.html"' in native
    assert 'href="skillevaluator-tier1.json"' in native
    assert 'href="skill-001/skillevaluator-tier1.html"' in index
    assert (tmp_path / "skill-001/skillevaluator-tier1.json").read_text() == raw
    assert "Content-Security-Policy" in native and "sha256-" in native and "unsafe-eval" not in native
    assert "<img src=x onerror=alert(1)>" not in native
    assert "https://example.com/run/skill-001/skillevaluator-tier1.html" in (tmp_path / "details.md").read_text()


def test_malformed_retained_evidence_is_not_silently_published(tmp_path):
    summary, _ = _write_fixture(tmp_path)
    path = tmp_path / "skill-001/skillevaluator-tier1.json"
    payload = json.loads(path.read_text())
    payload["results"][0]["passed"] = "true"
    path.write_text(json.dumps(payload))
    with pytest.raises(RetainedReportError):
        render_native_reports(tmp_path, summary, {})
    assert not (tmp_path / "index.html").exists()


def test_execution_error_overwrites_stale_html_with_honest_diagnostic(tmp_path):
    summary, _ = _write_fixture(tmp_path)
    summary["skills"][0].update(passed=False, overall_status="error", error="Process failed")
    render_native_reports(tmp_path, _summary(summary["skills"]), {})
    native = (tmp_path / "skill-001/skillevaluator-tier1.html").read_text()
    assert "Report unavailable" in native and "Process failed" in native
    assert "No passing result is claimed" in native and "ARTIFACT HTML" not in native
    assert "Incomplete" in (tmp_path / "index.html").read_text()
