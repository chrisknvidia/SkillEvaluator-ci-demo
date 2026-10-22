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
writes to a separate report directory. The artifact contains JSON, HTML,
Markdown, SARIF, and scanner logs. Missing tools, incomplete scans, absent
reports, and contradictory exit/report verdicts fail the job. Configure this job as a required check separately if you
want branch rules to prevent merging a failure.

## Reading results

The consumer runs on pull-request changes, pushes to `main`, and manual
**Skill checks** starts. Each run has three reporting surfaces:

- **GitHub run summary:** per-skill status, recorded quality score and grade,
  error/warning counts, scope, and validator evidence. Tier 2 and Tier 3 are
  explicitly **Not run**. Missing or inapplicable checks are not presented as
  successful execution.
- **Job logs and annotations:** the scan step prints each skill and validator
  outcome. Failed checks include recorded reasons, locations, and suggested
  fixes; annotations highlight a bounded set of actionable failures. Full
  scanner stdout/stderr remains in the downloadable artifact.
- **Hosted HTML:** a self-contained index includes scores, a **Needs attention**
  section, expandable per-skill check tables, exact findings, and supporting
  evidence. CI run conclusion is shown separately from the scanner verdict.

The configured report site is
[the consumer report history](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/).
After the trusted publisher deploys a run, its permanent path is
`runs/<run-id>/<attempt>/`; `main/latest/` points to the verified current main
report, and `pr/<number>/` points to the verified current same-repository PR
report. A delayed older run retains its history entry without replacing a
newer alias. Eligible PR runs create or update one bot comment with a concise
score table, failure reasons, and direct report/run links.

Hosted publication and bot-comment updates are being validated in this
experiment; these links and routes describe the configured reporting contract,
not proof that a new deployment has succeeded. While publication is pending,
open a run's **skill-evaluator-tier1** artifact and read `index.html` locally.
The trusted publisher rebuilds HTML from validated JSON and does not execute
PR content or reuse artifact-supplied HTML as trusted site content.

## Optional hosted reports and PR feedback setup

The base integration needs one consumer scan workflow: its run summary and
downloadable detailed reports work without a publisher. Hosted history and PR
comments require a second consumer workflow and this additional setup:

1. In the consumer repository, enable **Settings → Pages → Source: GitHub
   Actions**. Create a `gh-pages` branch containing `.nojekyll` and an empty
   `history.json` array (`[]`) before the first publication. This branch retains
   static report history; the publisher deploys it explicitly through Pages.
2. Add the companion consumer's
   [publisher workflow](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/blob/main/.github/workflows/publish-skill-reports.yml)
   to the consumer's default branch. Its `workflow_run` trigger follows completed
   **Skill checks** runs, including failures. Set `report-base-url` to that
   consumer's Pages URL; this demo uses
   `https://chrisknvidia.github.io/skill-evaluator-consumer-demo/`.
3. Pin the reusable publisher and evaluator workflows to reviewed commit SHAs.
   Set `trusted-evaluator-shas` to the approved evaluator SHA allowlist and
   `trusted-caller-blobs` to the exact approved Git blob of the consumer's
   `.github/workflows/skill-checks.yml`. From the consumer checkout, calculate it
   with `git hash-object .github/workflows/skill-checks.yml`. Changing that file
   requires explicitly reviewing and approving its new blob; retain older
   reviewed SHA/blob entries only when historical backfill needs them.
4. Keep the scan artifact's default name, **skill-evaluator-tier1**: the publisher
   accepts that specific artifact from approved **Skill checks** runs. Confine
   `contents: write`, `actions: read`, `pages: write`, `id-token: write`, and
   `pull-requests: write` to the separate publisher workflow. Its reusable jobs
   scope these permissions to history preparation, Pages deployment, and bot
   feedback respectively; the scan workflow keeps `contents: read`.

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
- Pinned SkillSpector v2.12.0 treats a quoted YAML version such as
  `metadata.version: "1.0.0"` as a missing file reference, making otherwise complete
  static analysis partial. The example skills use the equivalent valid YAML
  string `version: 1.0.0` to avoid this confirmed false positive. No scanner check
  or completeness requirement is disabled, and no upstream issue has been filed.
- Private registry authentication, plugin scanning, and Tier 2/3 are outside
  this demonstration. Hosted aliases and bot comments are limited to eligible
  runs from this consumer repository; publishing fork-PR reports is not enabled.
- Real credentialed LLM success has not been tested. The missing-key failure
  case proves configuration rejection only.
- The workflow has a 30-minute limit. Large collections need batching.

The live consumer runs and their downloaded reports are the runtime evidence;
local tests and successful image builds alone are not end-to-end proof.
