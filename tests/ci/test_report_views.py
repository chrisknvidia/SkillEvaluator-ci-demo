# SPDX-License-Identifier: Apache-2.0
"""Report presentation must preserve evidence, scope, and untrusted boundaries."""

import importlib.util
import json
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[2] / "ci" / "report_views.py"
SPEC = importlib.util.spec_from_file_location("ci_report_views", MODULE_PATH)
views = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(views)


def example(tmp_path, *, result=None):
    directory = tmp_path / "skill-001"
    directory.mkdir()
    result = result or {
        "validator": "Code risk",
        "passed": True,
        "status": "passed",
        "summary": {"checks_performed": 2, "errors": 0, "warnings": 0},
        "success_details": [{"check": "bandit", "message": "No issues"}],
    }
    data = {
        "overall_status": "passed",
        "overall_passed": True,
        "total_errors": 0,
        "total_warnings": 0,
        "results": [result],
        "quality_summary": [
            {
                "overall_score": 98.2,
                "grade": "A",
                "dimensions": {"correctness": {"score": 95, "weight": 0.35, "issues_count": 1}},
            }
        ],
        "workflow": {"stages": {"llm": {"status": "skipped", "reason": "Disabled by --no-llm"}}},
    }
    (directory / "skillevaluator-tier1.json").write_text(json.dumps(data))
    summary = {
        "total": 1,
        "passed": 1,
        "failed": 0,
        "incomplete": 0,
        "overall_status": "passed",
        "total_errors": 0,
        "total_warnings": 0,
        "skills": [{"path": "skills/sample", "report_dir": "skill-001", "overall_status": "passed", "passed": True}],
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary))
    return summary, data


def test_scores_scope_and_json_only_publish(tmp_path):
    summary, _ = example(tmp_path)
    original = (tmp_path / "summary.json").read_bytes()
    views.render_reports(
        tmp_path,
        summary,
        {"report_url": "https://example.com/reports/run-1", "run_url": "https://github.com/o/r/actions/runs/1"},
    )
    page = (tmp_path / "index.html").read_text()
    markdown = (tmp_path / "summary.md").read_text()
    comment = (tmp_path / "pr-comment.md").read_text()
    assert 'href="#skill-001"' in page
    assert "98.2" in page and "95" in page and "bandit" in page
    assert "Tier 2: Not run" in markdown and "Tier 3: Not run" in comment
    assert "LLM stages: skipped" in page and "Disabled by" in comment
    assert "https://example.com/reports/run-1/index.html" in comment
    assert "skillevaluator-tier1.html" not in page
    assert (tmp_path / "summary.json").read_bytes() == original


def test_failure_finding_location_and_suggestion_are_visible(tmp_path):
    result = {
        "validator": "Schema",
        "status": "failed",
        "passed": False,
        "summary": {"errors": 1, "warnings": 0, "checks_performed": 1},
        "findings": [
            {
                "check_name": "frontmatter_field",
                "severity": "high",
                "message": "Bad name",
                "file_path": "skills/sample/SKILL.md",
                "line_number": 2,
                "line_content": "name: BAD",
                "suggestion": "Use kebab-case",
            }
        ],
        "legacy": {"errors": ["Schema rejected the name"], "warnings": ["Additional advisory"]},
    }
    summary, _ = example(tmp_path, result=result)
    views.render_reports(tmp_path, summary, {})
    for file in ["index.html", "summary.md", "pr-comment.md"]:
        text = (tmp_path / file).read_text()
        assert "Bad name" in text and "Use kebab" in text and "SKILL" in text
    page = (tmp_path / "index.html").read_text()
    assert page.index("Needs attention") < page.index("Skills and scores")
    assert page.index("Bad name") < page.index("Skills and scores")
    assert "name: BAD" in page
    assert "Schema rejected the name" in (tmp_path / "summary.md").read_text()
    assert "Additional advisory" in (tmp_path / "index.html").read_text()


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            {"status": "passed", "passed": True, "success_details": [{"message": "No code - not applicable"}]},
            "NOT APPLICABLE",
        ),
        (
            {
                "status": "passed",
                "passed": True,
                "success_details": [{"message": "No code - not applicable"}, {"message": "Ran another check"}],
            },
            "PASS",
        ),
        ({"status": "incomplete", "passed": True}, "INCOMPLETE"),
        ({"status": "passed", "passed": True, "incomplete_scans": ["semgrep"]}, "INCOMPLETE"),
        ({"status": "skipped", "passed": False}, "NOT RUN"),
        ({"status": "skipped", "passed": True, "skip_reason": "Not applicable: no dependency files"}, "NOT APPLICABLE"),
        ({"status": "failed", "passed": True}, "FAIL"),
        ({"status": "passed"}, "UNKNOWN"),
        ({"status": {"malformed": True}}, "UNKNOWN"),
    ],
)
def test_outcomes_never_invent_success(payload, expected):
    assert views._status(payload) == expected


def test_untrusted_strings_and_urls_cannot_create_markup(tmp_path):
    summary, data = example(tmp_path)
    attack = '<script>alert("x")</script> [escape](javascript:alert(1)) |\n## forged'
    summary["skills"][0]["path"] = attack
    data["results"][0]["validator"] = attack
    data["results"][0]["success_details"][0]["message"] = attack
    (tmp_path / "skill-001/skillevaluator-tier1.json").write_text(json.dumps(data))
    views.render_reports(
        tmp_path,
        summary,
        {"run_url": "javascript:alert(1)", "report_url": "data:text/html,x", "image": attack, "commit": attack},
    )
    page = (tmp_path / "index.html").read_text()
    assert "<script>" not in page and "&lt;script&gt;" in page
    assert 'href="javascript:' not in page and 'href="data:' not in page
    assert "<script>" not in (tmp_path / "summary.md").read_text()
    assert "\\[escape\\]" in (tmp_path / "summary.md").read_text()
    assert "<script" not in page.lower() and "<iframe" not in page.lower()


@pytest.mark.parametrize("kind", ["missing", "malformed", "traversal", "symlink"])
def test_missing_or_unsafe_evidence_never_gets_green_score(tmp_path, kind):
    summary, _ = example(tmp_path)
    path = tmp_path / "skill-001/skillevaluator-tier1.json"
    if kind == "missing":
        path.unlink()
    elif kind == "malformed":
        path.write_text("[]")
    elif kind == "traversal":
        summary["skills"][0]["report_dir"] = "../outside"
    else:
        path.unlink()
        path.symlink_to(tmp_path / "summary.json")
    views.render_reports(tmp_path, summary, {})
    page = (tmp_path / "index.html").read_text()
    assert "INCOMPLETE" in page and "98.2" not in page
    assert "Not recorded" in page
    assert "Tier 1: executed for 0/1" in page


def test_summary_and_comment_limits_keep_complete_html(tmp_path):
    summary, data = example(tmp_path)
    data["results"][0]["legacy"] = {"warnings": ["Long finding " + "x" * (600 * 1024)]}
    data["results"][0]["status"] = "failed"
    data["results"][0]["passed"] = False
    (tmp_path / "skill-001/skillevaluator-tier1.json").write_text(json.dumps(data))
    views.render_reports(tmp_path, summary, {"report_url": "https://example.com/full"})
    assert (tmp_path / "summary.md").stat().st_size <= views.SUMMARY_LIMIT
    assert (tmp_path / "pr-comment.md").stat().st_size <= views.COMMENT_LIMIT
    assert "Truncated for CI display limits" in (tmp_path / "summary.md").read_text()
    assert "x" * (600 * 1024) in (tmp_path / "index.html").read_text()
    assert "https://example.com/full/index.html" in (tmp_path / "pr-comment.md").read_text()


def test_output_symlink_is_rejected(tmp_path):
    summary, _ = example(tmp_path)
    target = tmp_path / "original.txt"
    target.write_text("preserve")
    (tmp_path / "index.html").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        views.render_reports(tmp_path, summary, {})
    assert target.read_text() == "preserve"


def test_github_mentions_are_neutralized_in_all_markdown_views(tmp_path):
    summary, data = example(tmp_path)
    summary["skills"][0]["path"] = "skills/@some-user/@some-org/team"
    data["results"][0]["status"] = "failed"
    data["results"][0]["findings"] = [
        {"message": "Ask @some-user and @some-org/team", "suggestion": "Contact @some-user"}
    ]
    (tmp_path / "skill-001/skillevaluator-tier1.json").write_text(json.dumps(data))
    views.render_reports(tmp_path, summary, {"commit": "@some-user", "image": "@some-org/team"})
    for filename in ["summary.md", "pr-comment.md"]:
        text = (tmp_path / filename).read_text()
        assert "@some-user" not in text
        assert "@some-org" not in text
        assert "@\u200bsome" in text
    # Original retained evidence is not rewritten by the presentation adapter.
    assert "@some-user" in (tmp_path / "skill-001/skillevaluator-tier1.json").read_text()


@pytest.mark.parametrize(
    "result",
    [
        {
            "validator": "SCRIPT_LINT",
            "success_details": [{"check": "lint", "message": "No scripts/ or tools/ directory found"}],
        },
        {
            "validator": "Semantic Version Validation",
            "success_details": [
                {"check": "version_optional", "message": "No version supplied; version validation is optional"}
            ],
        },
    ],
)
def test_optional_or_absent_targets_are_not_reported_as_executed_passes(result):
    result.update({"status": "passed", "passed": True})
    assert views._status(result) == "NOT APPLICABLE"
    assert views._evidence(result)[0][1] == result["success_details"][0]["message"]


@pytest.mark.parametrize("change", ["missing_boolean", "opposite_boolean", "opposite_status", "summary_count"])
def test_inconsistent_verdicts_never_display_a_passing_skill(tmp_path, change):
    summary, data = example(tmp_path)
    if change == "missing_boolean":
        data.pop("overall_passed")
    elif change == "opposite_boolean":
        summary["skills"][0]["passed"] = False
    elif change == "opposite_status":
        summary["skills"][0]["overall_status"] = "failed"
    else:
        summary["passed"] = 0
    (tmp_path / "skill-001/skillevaluator-tier1.json").write_text(json.dumps(data))
    views.render_reports(tmp_path, summary, {})
    page = (tmp_path / "index.html").read_text()
    assert "INCOMPLETE" in page
    if change != "summary_count":
        assert "Summary and child report verdicts" in page


def test_ci_run_conclusion_is_separate_from_scan_result(tmp_path):
    summary, _ = example(tmp_path)
    views.render_reports(tmp_path, summary, {"ci_conclusion": "failure"})
    for filename in ["summary.md", "index.html", "pr-comment.md"]:
        text = (tmp_path / filename).read_text()
        assert "CI run conclusion" in text and "failure" in text
        assert "PASSED" in text
