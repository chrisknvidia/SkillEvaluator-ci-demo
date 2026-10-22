# Live CI verification — 2026-10-22 UTC

The complete no-LLM Tier 1 workflow was executed by a separate GitHub repository.
The evidence below includes downloaded and inspected reports, not only workflow
status. This is an experimental personal fork, not an official NVIDIA release.

## Exact runtime

- Upstream source: NVIDIA/SkillEvaluator at `2085a03d89f98525239080e06069d447e1de8f4a`.
- Image source: this fork at `03ee78b91d9931d4a1955ae58f68f8729990ec94`.
- [Successful image build and publication](https://github.com/chrisknvidia/SkillEvaluator-ci-demo/actions/runs/39709857075).
- Image: `ghcr.io/chrisknvidia/skillevaluator-ci-demo@sha256:3d58dad8aca60a110832c685bfdb29d488089f05d4746bfdb1272f93b456db41`.
- [Public container package](https://github.com/users/chrisknvidia/packages/container/package/skillevaluator-ci-demo).
- Reusable workflow: `3dfc2616a354e313ae430782744f2100b0ce5bef`.
- Passing consumer commit: `6da096f62206fd9e1aecc89c170a5dc4af31303f`.

The customer workflow supplies only skill paths and `llm: false`. It pulls the
image using an empty Docker credential configuration. No registry credential or
model secret is needed for the static run.

## Observed results

| Case | Actual outcome | Evidence |
| --- | --- | --- |
| Five valid skills | Passed; all 60 validator results passed, no errors or incomplete scans | [Hosted run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39710504103) |
| PR adds one invalid skill | Failed; five passed, one failed, all six scanned, no incomplete scans | [Draft PR](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/pull/1), [hosted run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39710576857) |
| Missing configured directory | Failed configuration and retained summary explaining the missing path | [Hosted run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39710658643) |
| LLM requested without a key | Failed configuration and retained summary explaining the missing key | [Hosted run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39710662441) |

The successful run contains actual SkillSpector and Gitleaks completion evidence
for every skill. The Python/dependency fixture additionally records successful
Bandit, Semgrep, and pip-audit execution. Applicability is respected: code and
dependency tools do not need to run on text-only skills without dependencies.

JSON, HTML, Markdown, and SARIF were independently inspected. All agree on
completed Tier 1 processing. SARIF reports successful execution without
incomplete-scan notifications. Six advisory findings and 16 warnings remain;
passing is not the same as finding-free. Publication eligibility remains
incomplete because this demonstration runs only Tier 1.

Additional real local container checks established that removing Semgrep makes
the result incomplete with exit 1 while other scanners complete. Unchanged
pip-audit commands passed a clean manifest and resolved transitive dependencies
for a separate vulnerable manifest, preserving findings and a failing verdict.
Those checks used the locally built ARM64 image; the hosted consumer used amd64.
An independent code review found no blocking issues for the demo; 31 focused
wrapper tests also passed.

## Problems uncovered and resolved for the demo

1. Build-time Semgrep settings were root-owned. The image now removes that state
   and initializes a writable home for its non-root runtime.
2. Docker's temporary mount was non-executable, preventing pip-audit's resolver
   from running. The workflow supplies a separate executable `/audit-tmp` and
   sets `TMPDIR`; `/tmp` stays non-executable, and the root filesystem and input
   checkout stay read-only. Dependency resolution remains enabled.
3. SkillSpector v2.12.0 misreads quoted YAML `version: "1.0.0"` as a missing local
   file reference. The examples use the semantically identical unquoted scalar
   `version: 1.0.0`. The upstream scanner defect remains; no scanner was disabled
   and no completeness requirement was weakened.

## Verification boundaries

Credentialed LLM success was not tested and no provider key was added. Tier 2,
Tier 3, plugin scanning, Windows/macOS runners, and fork-origin pull requests were
not tested. The invalid-skill PR is a same-repository branch PR. Branch rules do
not require this check for merging; configure that separately if desired.
Reports retained as workflow artifacts expire after 14 days. Workflow/run links
and this record remain available.

Consumers are pinned to the tested immutable image. Rebuilding the image is a
new verification event: not all base-image and scanner transitive dependencies
are locked to digests or hashes in this experimental publisher.
