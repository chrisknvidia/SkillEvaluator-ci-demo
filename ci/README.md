# Experimental reusable Tier 1 CI

This personal fork demonstrates a complete Tier 1 runtime consumed by a separate
GitHub repository. It is an experiment, not an official NVIDIA integration.
The upstream repository is unchanged.

## Consumer setup

The companion repository is
[skill-evaluator-consumer-demo](https://github.com/chrisknvidia/skill-evaluator-consumer-demo).
Its `.github/workflows/skill-checks.yml` is the runnable customer example.
Consumers provide newline-separated paths; the reusable workflow discovers each
`SKILL.md`, pulls a prebuilt image, evaluates every skill, preserves reports even
when validation fails, and sets the job result from both process and report evidence.

The canonical command inside the image is:

```bash
skillevaluator tier1 /workspace/skills/example --no-llm --profile external \
  -r json,html,markdown,sarif -o /reports/skill-001
```

No check selector is supplied: this includes all Tier 1 checks and dependency
auditing. Tools that do not apply to a skill's files remain not applicable.
Tier 2 and Tier 3 do not run. A Tier 1 pass does not establish publication eligibility
or that the skill performs its intended task correctly.

## Runtime and results

`ci/Dockerfile.tier1` installs SkillEvaluator from the fork's lockfile with the
security and LLM extras, Semgrep 1.182.0, SkillSpector v2.12.0 at a fixed commit,
and checksum-verified Gitleaks 8.30.0. Scanners have independent Python environments
where needed. `Publish demo Tier 1 image` builds and pushes the image to GHCR.
The package must be Public for anonymous consumer pulls. The consumer workflow
must pin the published digest before the live example is considered verified.

The runtime reads a read-only checkout, runs without elevated privileges, and
writes to a separate report directory. The workflow summary links the verdict to
each skill. The artifact contains JSON, HTML, Markdown, SARIF, and scanner logs.
Missing tools, incomplete scans, absent reports, and contradictory exit/report
verdicts fail the job. Configure this job as a required check separately if you
want branch rules to prevent merging a failure.

## Optional LLM checks

The default is `llm: false`, with no provider credential required. To add LLM
security analysis, finding verification, and rubric evaluation, set `llm: true`,
choose `llm-provider` (`openai`, `anthropic`, or `nv_build`), optionally set
`llm-model`, and explicitly pass the repository secret `LLM_API_KEY`.
Use a trusted manual run for this option; fork pull requests do not receive secrets.
Missing credentials fail explicitly. The model provider bills the caller.

## Deliberate limits of this demonstration

- Linux GitHub-hosted runners; the published demonstration image is amd64.
- At most 100 skills per invocation, with exact-case `SKILL.md` discovery.
- Paths must be repository-relative directories. Symlinks are rejected.
- The default is network-connected static scanning: vulnerability databases can
  receive dependency metadata even when LLM checks are disabled.
- Private registry authentication, plugin scanning, Tier 2/3, and automatic PR
  comments are outside this demonstration.
- The workflow has a 30-minute limit. Large collections need batching.

The live consumer runs and their downloaded reports are the runtime evidence;
local tests and successful image builds alone are not end-to-end proof.
