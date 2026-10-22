# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""Test the CI adapter's boundaries; actual scanner coverage is tested by live CI."""

import importlib.util
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

MODULE_PATH = Path(__file__).parents[2] / "ci" / "run_tier1.py"
SPEC = importlib.util.spec_from_file_location("ci_run_tier1", MODULE_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def skill(workspace, path):
    directory = workspace / path
    directory.mkdir(parents=True)
    (directory / "SKILL.md").write_text("---\nname: example\n---\n", encoding="utf-8")
    return directory


def payload(passed=True, status="passed", incomplete=None):
    return {
        "overall_passed": passed,
        "overall_status": status,
        "incomplete_scans": incomplete or [],
        "total_validators": 12,
        "total_errors": 0 if passed else 1,
        "total_warnings": 0,
        "severity_counts": {"critical": 0, "high": 0 if passed else 1, "medium": 0, "low": 0},
        "results": [{"passed": passed, "status": status} for _ in range(12)],
    }


def fake_cli(responses, calls):
    def invoke(argv, **kwargs):
        calls.append((argv, kwargs))
        exit_code, report = responses[len(calls) - 1]
        kwargs["stdout"].write(b"::error::untrusted scanner text\n")
        output = Path(argv[argv.index("-o") + 1])
        if report is not None:
            (output / "skillevaluator-tier1.json").write_text(json.dumps(report), encoding="utf-8")
        return CompletedProcess(argv, exit_code)

    return invoke


def test_selection_deduplicates_overlapping_roots(tmp_path):
    first = skill(tmp_path, "skills/a")
    second = skill(tmp_path, "skills/b")
    assert runner.discover_skills(tmp_path, "skills\nskills/a\nskills") == [first, second]


@pytest.mark.parametrize("root", ["/etc", "../skills", "skills/../other", "C:\\skills", "skills\\a"])
def test_rejects_unsafe_roots(tmp_path, root):
    with pytest.raises(runner.ConfigurationError):
        runner.discover_skills(tmp_path, root)


def test_empty_selection_and_missing_root_fail(tmp_path):
    for roots in ("", "skills"):
        with pytest.raises(runner.ConfigurationError):
            runner.discover_skills(tmp_path, roots)
    (tmp_path / "skills").mkdir()
    with pytest.raises(runner.ConfigurationError):
        runner.discover_skills(tmp_path, "skills")


@pytest.mark.parametrize("link_kind", ["root", "ancestor", "file", "directory"])
def test_rejects_symlinks_anywhere_in_tree(tmp_path, link_kind):
    target = skill(tmp_path, "skills/a")
    if link_kind == "root":
        (tmp_path / "alias").symlink_to(target, target_is_directory=True)
        configured = "alias"
    elif link_kind == "ancestor":
        (tmp_path / "alias").symlink_to(tmp_path / "skills", target_is_directory=True)
        configured = "alias/a"
    else:
        (target / "linked").symlink_to(target if link_kind == "directory" else target / "SKILL.md")
        configured = "skills"
    with pytest.raises(runner.ConfigurationError):
        runner.discover_skills(tmp_path, configured)


def test_target_limit_is_global(tmp_path):
    for index in range(101):
        skill(tmp_path, f"skills/a{index:03d}")
    with pytest.raises(runner.ConfigurationError):
        runner.discover_skills(tmp_path, "skills")


def test_all_skills_run_after_failure_and_scanner_stdout_is_not_printed(tmp_path, capsys):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/a")
    skill(workspace, "skills/b")
    calls = []
    reports = tmp_path / "reports"
    exit_code = runner.run(
        workspace,
        reports,
        {"SKILL_PATHS": "skills", "LLM_ENABLED": "false"},
        execute=fake_cli([(1, payload(False, "failed")), (0, payload())], calls),
    )
    summary = json.loads((reports / "summary.json").read_text())
    assert exit_code == 1
    assert len(calls) == 2
    assert (summary["total"], summary["passed"], summary["failed"]) == (2, 1, 1)
    assert summary["total_validators"] == 24
    assert "::error::" not in capsys.readouterr().out
    assert "::error::" in (reports / "skill-001" / "stdout.log").read_text()
    assert "--no-llm" in calls[0][0]
    assert calls[0][1]["env"]["HOME"] == "/tmp/evaluator-home"


def test_structured_failure_logs_and_annotations_are_escaped(capsys):
    row = {"path": "skills/example", "overall_status": "failed"}
    report = {
        "quality_summary": [{"overall_score": 71.8, "grade": "C"}],
        "results": [
            {
                "validator": "Schema,metadata",
                "status": "failed",
                "passed": False,
                "findings": [
                    {
                        "severity": "high",
                        "message": "Bad name\n::notice::injected",
                        "suggestion": "Use kebab-case",
                        "file_path": "/workspace/skills/example/SKILL.md",
                        "line_number": None,
                    }
                ],
            }
        ],
    }
    runner.log_result(row, report, annotations=True, budget={"errors": 0})
    output = capsys.readouterr().out
    assert "71.8/100" in output
    assert "Suggested fix:" in output
    assert "\n::notice::injected" not in output
    commands = [line for line in output.splitlines() if line.startswith("::")]
    assert len(commands) == 1
    assert "title=Schema%2Cmetadata,file=skills/example/SKILL.md" in commands[0]
    assert "Bad name%0A::notice::injected" in commands[0]
    assert ",line=" not in commands[0]


def test_annotation_budget_does_not_hide_log_details(capsys):
    row = {"path": "skills/example", "overall_status": "failed"}
    report = {
        "results": [
            {
                "validator": "Schema",
                "status": "failed",
                "passed": False,
                "findings": [{"severity": "high", "message": "Bad metadata"}],
            }
        ]
    }
    runner.log_result(row, report, annotations=True, budget={"errors": 10})
    output = capsys.readouterr().out
    assert "Bad metadata" in output
    assert "::error" not in output


@pytest.mark.parametrize(
    "exit_code,report",
    [
        (0, None),
        (0, {}),
        (1, payload()),
        (0, payload(False, "failed")),
        (0, payload(True, "incomplete", ["semgrep"])),
        (0, {**payload(), "results": [{"passed": False, "status": "failed"}]}),
        (0, {**payload(), "overall_passed": "true"}),
        (0, {**payload(), "total_validators": 100}),
        (0, {**payload(), "results": [{"passed": True, "status": "incomplete"}] * 12}),
    ],
)
def test_exit_or_report_disagreement_never_passes(tmp_path, exit_code, report):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/a")
    reports = tmp_path / "reports"
    result = runner.run(workspace, reports, {"SKILL_PATHS": "skills"}, execute=fake_cli([(exit_code, report)], []))
    assert result == 1
    assert json.loads((reports / "summary.json").read_text())["overall_passed"] is False


def test_llm_maps_only_explicit_provider_and_credentials(tmp_path):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/a")
    calls = []
    environment = {
        "SKILL_PATHS": "skills",
        "LLM_ENABLED": "true",
        "LLM_PROVIDER": "nv_build",
        "LLM_API_KEY": "test-key",
        "LLM_MODEL": "test-model",
        "OPENAI_API_KEY": "ambient-key",
        "SKILLSPECTOR_PROVIDER": "untrusted-ambient-provider",
        "SKILL_EVAL_LLM_BASE_URL": "https://unexpected.invalid",
    }
    assert runner.run(workspace, tmp_path / "reports", environment, execute=fake_cli([(0, payload())], calls)) == 0
    argv, kwargs = calls[0]
    assert "--llm" in argv
    assert kwargs["env"]["NVIDIA_API_KEY"] == "test-key"
    assert kwargs["env"]["SKILL_EVAL_LLM_PROVIDER"] == "nv_build"
    assert kwargs["env"]["SKILL_EVAL_LLM_MODEL"] == "test-model"
    assert "OPENAI_API_KEY" not in kwargs["env"]
    assert "SKILLSPECTOR_PROVIDER" not in kwargs["env"]
    assert "SKILL_EVAL_LLM_BASE_URL" not in kwargs["env"]


@pytest.mark.parametrize(
    "extra",
    [
        {"LLM_ENABLED": "true"},
        {"LLM_ENABLED": "true", "LLM_PROVIDER": "arbitrary", "LLM_API_KEY": "key"},
        {"LLM_ENABLED": "yes"},
    ],
)
def test_invalid_llm_configuration_is_reported_without_running(tmp_path, extra):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/a")
    reports = tmp_path / "reports"
    calls = []
    assert runner.run(workspace, reports, {"SKILL_PATHS": "skills", **extra}, execute=fake_cli([], calls)) == 1
    assert not calls
    assert json.loads((reports / "summary.json").read_text())["overall_status"] == "error"


def test_markdown_paths_cannot_inject_html_or_table_rows(tmp_path):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/<script>|[x]`danger`")
    reports = tmp_path / "reports"
    assert runner.run(workspace, reports, {"SKILL_PATHS": "skills"}, execute=fake_cli([(0, payload())], [])) == 0
    markdown = (reports / "summary.md").read_text()
    assert "<script>" not in markdown
    assert "&lt;script&gt;" in markdown
    assert "\\|" in markdown


def test_successful_rollup_preserves_all_counts(tmp_path):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/a")
    reports = tmp_path / "reports"
    assert runner.run(workspace, reports, {"SKILL_PATHS": "skills"}, execute=fake_cli([(0, payload())], [])) == 0
    summary = json.loads((reports / "summary.json").read_text())
    assert summary["overall_passed"] is True
    assert summary["overall_status"] == "passed"
    assert summary["incomplete"] == 0
    assert summary["skills"][0]["path"] == "skills/a"


def test_invalid_json_is_reported_and_later_skills_still_run(tmp_path):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/a")
    skill(workspace, "skills/b")
    reports = tmp_path / "reports"
    calls = []
    original = fake_cli([(0, payload()), (0, payload())], calls)

    def invoke(argv, **kwargs):
        completed = original(argv, **kwargs)
        if len(calls) == 1:
            output = Path(argv[argv.index("-o") + 1])
            (output / "skillevaluator-tier1.json").write_text("not json", encoding="utf-8")
        return completed

    assert runner.run(workspace, reports, {"SKILL_PATHS": "skills"}, execute=invoke) == 1
    summary = json.loads((reports / "summary.json").read_text())
    assert summary["incomplete"] == 1
    assert summary["passed"] == 1
    assert len(calls) == 2


def test_process_start_error_does_not_skip_later_skills(tmp_path):
    workspace = tmp_path / "workspace"
    skill(workspace, "skills/a")
    skill(workspace, "skills/b")
    reports = tmp_path / "reports"
    calls = []

    def invoke(argv, **kwargs):
        calls.append(argv)
        if len(calls) == 1:
            raise OSError("untrusted failure text")
        output = Path(argv[argv.index("-o") + 1])
        (output / "skillevaluator-tier1.json").write_text(json.dumps(payload()), encoding="utf-8")
        return CompletedProcess(argv, 0)

    assert runner.run(workspace, reports, {"SKILL_PATHS": "skills"}, execute=invoke) == 1
    assert len(calls) == 2


def test_static_run_does_not_receive_ambient_model_credentials():
    env, enabled = runner.child_environment(
        {
            "LLM_ENABLED": "false",
            "LLM_API_KEY": "secret",
            "OPENAI_API_KEY": "ambient",
            "SKILL_EVAL_LLM_PROVIDER": "openai",
            "SKILLSPECTOR_PROVIDER": "anthropic",
        }
    )
    assert enabled is False
    assert not any("KEY" in name or "PROVIDER" in name for name in env)
    assert env["PYTHON_DOTENV_DISABLED"] == "1"
    assert env["SEMGREP_SEND_METRICS"] == "off"
    assert env["SEMGREP_ENABLE_VERSION_CHECK"] == "0"
