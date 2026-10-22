# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
# ruff: noqa: INP001, T201 -- standalone CI entrypoint; stdout contains fixed progress only.

"""Run complete Tier 1 checks on configured repository skills and retain evidence.

This adapter deliberately emits only fixed progress messages on stdout. Scanner
output belongs in artifacts, never in the GitHub workflow-command stream.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
from pathlib import Path

MAX_SKILLS = 100
MAX_REPORT_BYTES = 32 * 1024 * 1024
PROVIDER_KEYS = {"openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "nv_build": "NVIDIA_API_KEY"}
PROCESS_ENV = {
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
}


class ConfigurationError(ValueError):
    """An invalid request, without echoing untrusted paths or credentials."""


def discover_skills(workspace: Path, roots: str) -> list[Path]:
    """Discover a bounded unique set; any linked scan content is rejected."""
    workspace = workspace.resolve(strict=True)
    configured = [line.strip() for line in roots.splitlines() if line.strip()]
    if not configured:
        raise ConfigurationError("SKILL_PATHS must contain at least one relative directory.")
    discovered: set[Path] = set()
    for raw in configured:
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts or "\\" in raw or ":" in raw:
            raise ConfigurationError("Skill roots must be relative directories without parent traversal.")
        current = workspace
        for part in relative.parts:
            current /= part
            if current.is_symlink():
                raise ConfigurationError("Symlinks are not supported in skill roots or scan content.")
        root = workspace / relative
        if not root.is_dir() or not root.resolve(strict=True).is_relative_to(workspace):
            raise ConfigurationError("A configured skill root is missing or outside the workspace.")

        def inaccessible(_error):
            raise ConfigurationError("A skill directory could not be read.")

        for directory, directories, files in os.walk(root, followlinks=False, onerror=inaccessible):
            parent = Path(directory)
            for name in [*directories, *files]:
                child = parent / name
                if child.is_symlink():
                    raise ConfigurationError("Symlinks are not supported in skill roots or scan content.")
                if not child.is_dir() and not child.is_file():
                    raise ConfigurationError("Only regular files and directories are supported in skill trees.")
            if "SKILL.md" in files:
                discovered.add(parent)
                if len(discovered) > MAX_SKILLS:
                    raise ConfigurationError("The CI integration supports at most 100 skills per run.")
    if not discovered:
        raise ConfigurationError("No SKILL.md files were found under the configured skill roots.")
    return sorted(discovered, key=lambda item: item.relative_to(workspace).as_posix())


def child_environment(environ: dict[str, str]) -> tuple[dict[str, str], bool]:
    """Limit provider selection to the explicit CI inputs, including static runs."""
    enabled = environ.get("LLM_ENABLED", "false").strip().lower()
    if enabled not in {"true", "false"}:
        raise ConfigurationError("LLM_ENABLED must be true or false.")
    env = {key: value for key, value in environ.items() if key in PROCESS_ENV}
    env.setdefault("PATH", os.defpath)
    env["HOME"] = "/tmp/evaluator-home"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHON_DOTENV_DISABLED"] = "1"
    env["SEMGREP_SEND_METRICS"] = "off"
    env["SEMGREP_ENABLE_VERSION_CHECK"] = "0"
    env["NO_COLOR"] = "1"
    Path(env["HOME"]).mkdir(parents=True, exist_ok=True)
    if enabled == "true":
        provider = environ.get("LLM_PROVIDER", "").strip()
        if provider not in PROVIDER_KEYS:
            raise ConfigurationError("LLM_PROVIDER must be openai, anthropic, or nv_build when LLM is enabled.")
        key = environ.get("LLM_API_KEY", "").strip()
        if not key:
            raise ConfigurationError("LLM_API_KEY is required when LLM_ENABLED is true.")
        env["SKILL_EVAL_LLM_PROVIDER"] = provider
        env[PROVIDER_KEYS[provider]] = key
        model = environ.get("LLM_MODEL", "").strip()
        if model:
            if any(ord(character) < 32 for character in model):
                raise ConfigurationError("LLM_MODEL must not contain control characters.")
            env["SKILL_EVAL_LLM_MODEL"] = model
    return env, enabled == "true"


def markdown_text(value: str) -> str:
    value = "".join(character if ord(character) >= 32 else f"\\u{ord(character):04x}" for character in value)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~-])", r"\\\1", html.escape(value, quote=True))


def _write_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    temporary.replace(path)


def _load_report(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
        raise ValueError("The evaluator did not produce a readable JSON report.")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("The evaluator JSON report is malformed.")
    if type(data.get("overall_passed")) is not bool:
        raise ValueError("The evaluator JSON report lacks a boolean verdict.")
    if data.get("overall_status") not in {"passed", "failed", "incomplete"}:
        raise ValueError("The evaluator JSON report lacks a recognized status.")
    scans = data.get("incomplete_scans")
    if not isinstance(scans, list) or any(not isinstance(scan, str) for scan in scans):
        raise ValueError("The evaluator JSON report lacks scanner completeness evidence.")
    results = data.get("results")
    if not isinstance(results, list) or not results or any(not isinstance(result, dict) for result in results):
        raise ValueError("The evaluator JSON report lacks validator results.")
    for name in ("total_validators", "total_errors", "total_warnings"):
        if type(data.get(name)) is not int or data[name] < 0:
            raise ValueError("The evaluator JSON report has invalid result counts.")
    if data["total_validators"] != len(results):
        raise ValueError("The evaluator JSON report has inconsistent validator counts.")
    counts = data.get("severity_counts")
    if not isinstance(counts, dict) or any(
        type(counts.get(name)) is not int or counts[name] < 0 for name in ("critical", "high", "medium", "low")
    ):
        raise ValueError("The evaluator JSON report has invalid severity counts.")
    return data


def _summary(skills: list[dict], error: str | None = None) -> dict:
    passed = sum(item["passed"] for item in skills)
    incomplete = sum(item["overall_status"] in {"incomplete", "error"} for item in skills)
    payload = {
        "total": len(skills),
        "passed": passed,
        "failed": len(skills) - passed,
        "incomplete": incomplete,
        "overall_passed": bool(skills) and passed == len(skills) and error is None,
        "overall_status": "error"
        if error
        else "incomplete"
        if incomplete
        else "passed"
        if passed == len(skills) and skills
        else "failed",
        "total_validators": sum(item.get("total_validators", 0) for item in skills),
        "total_errors": sum(item.get("total_errors", 0) for item in skills),
        "total_warnings": sum(item.get("total_warnings", 0) for item in skills),
        "severity_counts": {
            name: sum(item.get("severity_counts", {}).get(name, 0) for item in skills)
            for name in ("critical", "high", "medium", "low")
        },
        "skills": skills,
    }
    if error:
        payload["error"] = error
    return payload


def _write_summary(reports: Path, summary: dict) -> None:
    _write_json(reports / "summary.json", summary)
    lines = [
        "# SkillEvaluator Tier 1",
        "",
        f"Result: **{summary['overall_status']}**",
        "",
        f"Skills: {summary['total']} | Passed: {summary['passed']} | Failed: {summary['failed']} | Incomplete: {summary['incomplete']}",
        "",
    ]
    if summary.get("error"):
        lines.extend([markdown_text(summary["error"]), ""])
    lines.extend(["| Skill | Exit code | Status | Incomplete scanners |", "| --- | --- | --- | --- |"])
    for item in summary["skills"]:
        scans = ", ".join(item["incomplete_scans"]) or "none"
        lines.append(
            f"| {markdown_text(item['path'])} | {item['exit_code']} | {item['overall_status']} | {markdown_text(scans)} |"
        )
    temporary = reports / "summary.md.tmp"
    with temporary.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    temporary.replace(reports / "summary.md")


def run(workspace: Path, reports: Path, environ: dict[str, str], *, execute=subprocess.run) -> int:
    """Run all selected skills; return nonzero on every incomplete or failed run."""
    if reports.is_symlink():
        raise ConfigurationError("The report directory must not be a symlink.")
    reports.mkdir(parents=True, exist_ok=True)
    if any(reports.iterdir()):
        raise ConfigurationError("The report directory must be empty to avoid stale evidence.")
    reports = reports.resolve(strict=True)
    rows = []
    try:
        workspace = workspace.resolve(strict=True)
        if reports.is_relative_to(workspace):
            raise ConfigurationError("The report directory must be outside the read-only workspace.")
        env, llm = child_environment(environ)
        selected = discover_skills(workspace, environ.get("SKILL_PATHS", "skills"))
    except (ConfigurationError, OSError) as exc:
        message = (
            str(exc)
            if isinstance(exc, ConfigurationError)
            else "The workspace or runtime configuration could not be read."
        )
        _write_summary(reports, _summary([], error=message))
        print("SkillEvaluator configuration failed.", flush=True)
        return 1
    for index, target in enumerate(selected, 1):
        print(f"SkillEvaluator: evaluating skill {index} of {len(selected)}.", flush=True)
        output = reports / f"skill-{index:03d}"
        output.mkdir()
        row = {
            "path": target.relative_to(workspace).as_posix(),
            "report_dir": output.name,
            "exit_code": None,
            "overall_status": "error",
            "incomplete_scans": [],
            "passed": False,
        }
        argv = [
            "skillevaluator",
            "tier1",
            str(target),
            "--llm" if llm else "--no-llm",
            "--profile",
            "external",
            "-r",
            "json,html,markdown,sarif",
            "-o",
            str(output),
        ]
        try:
            with (output / "stdout.log").open("xb") as stdout, (output / "stderr.log").open("xb") as stderr:
                process = execute(argv, cwd=workspace, env=env, stdout=stdout, stderr=stderr, check=False)
            row["exit_code"] = process.returncode
            data = _load_report(output / "skillevaluator-tier1.json")
            for key in (
                "overall_status",
                "incomplete_scans",
                "total_validators",
                "total_errors",
                "total_warnings",
                "severity_counts",
            ):
                row[key] = data[key]
            row["passed"] = (
                process.returncode == 0
                and data["overall_passed"] is True
                and data["overall_status"] == "passed"
                and not data["incomplete_scans"]
                and all(
                    result.get("passed") is True
                    and result.get("status") not in {"incomplete", "failed"}
                    and not result.get("incomplete_scans")
                    for result in data["results"]
                )
            )
            if not row["passed"] and row["overall_status"] == "passed":
                row["overall_status"] = "error"
                row["error"] = "Process exit or validator results contradict the report verdict."
        except (OSError, ValueError, UnicodeError, RecursionError):
            row["error"] = "Evaluator execution failed or its JSON report was missing, unreadable, or invalid."
        rows.append(row)
    summary = _summary(rows)
    _write_summary(reports, summary)
    print(f"SkillEvaluator finished: {summary['passed']} of {summary['total']} skills passed.", flush=True)
    return 0 if summary["overall_passed"] else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path("/workspace"))
    parser.add_argument("--reports", type=Path, default=Path("/reports"))
    args = parser.parse_args()
    try:
        return run(args.workspace, args.reports, dict(os.environ))
    except (ConfigurationError, OSError):
        print("SkillEvaluator could not safely initialize the report directory.", flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
