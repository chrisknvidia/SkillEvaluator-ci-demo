# Live CI verification — 2026-10-22 UTC

## Native HTML redesign: verified live

The consumer now uses SkillEvaluator's native HTML reports, with a small
multi-skill index linking to each report. The design includes a clear outcome,
actionable findings, separate quality scores, search and combined filters,
keyboard controls, dark mode, mobile layouts, offline evidence and print.
N/A and incomplete outcomes remain distinct from successful execution.
The original JSON evidence and all gating semantics are preserved.

- Image source: `29734ecaa6d905f6026f59e1f91115aee24a0ac6`.
- [Successful image publication](https://github.com/chrisknvidia/SkillEvaluator-ci-demo/actions/runs/39844001501).
- Image: `ghcr.io/chrisknvidia/skillevaluator-ci-demo@sha256:9a8a1300d636a941ab1f718dc4decac99988b1331de2f8e5c0473ca22f2024bb`.
- Reusable workflows: `48cceecb6533d6d3ec785b0e62c45f0a74a9d5ec`.
- Main commit: `f040cc83dae10db93f41f0ab769b2e8e909f6cb3`.
- PR commit: `0a2ab6e1d76ff258a734ebd5ec3fa3ace6575c61`.

| Case | Inspected result | Evidence |
| --- | --- | --- |
| Main scan | 5/5 pass; 60 validator rows; 0 errors; quality 98.2/A each | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39844363192), [report](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/runs/39844363192/1/) |
| Invalid-skill PR | 5 pass, 1 fail; 72 rows; 2 errors; invalid skill 71.8/C | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39844380707), [native failure report](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/runs/39844380707/1/skill-004/skillevaluator-tier1.html) |
| Missing path | Configuration ERROR, zero checks, readable retained report | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39844374811) |
| Missing LLM key | Configuration ERROR, zero checks, explicit missing-key reason | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39844379119) |
| Main publication | Native rendering, history and Pages deployment succeeded | [Publisher](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39844590015) |
| PR publication | Native rendering, Pages and comment update succeeded | [Publisher](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39844640613) |

The same [bot comment](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/pull/1#issuecomment-6334583529)
now identifies the final PR commit and run. Its rendered six-row table, scores,
two failure explanations and fixes were read back from GitHub. All 11 hosted
per-skill JSON reports exactly match the downloaded CI data.

Independent source review and hosted Chromium checks passed: index-to-report
navigation, canonical JSON downloads, filters, keyboard controls, dark mode,
JavaScript-disabled evidence, print, and mobile widths of 320/390 pixels.
Published pages had no JavaScript or content-policy errors. Both stable aliases
resolve to the final immutable runs and identify the expected commit and image.
Hostile strings remained escaped; Tier 1 pages make no external resource requests.
The trusted publisher regenerates HTML from bounded JSON, using pinned native
templates and exact script/handler hashes rather than publishing artifact HTML.

In an isolated environment using the frozen dependencies, **1,089 tests passed**
and five optional Streamlit-dashboard tests were skipped. The wheel contains
the exact native templates and adapter, and rendered a real failed report when
imported directly. An initial broad run caught missing combined-tier gate-policy
labels; these were restored conditionally and the complete final suite passed.
Combined Tier 2/3 UI fixtures were also inspected in a browser. Real LLM success
and Tier 2/3 agent execution remain outside this Tier 1 demonstration.

## Reporting follow-up: verified live

The reporting extension was tested with a rebuilt public image and fresh consumer
runs. It provides detailed GitHub summaries, failed-check annotations, hosted
HTML, retained run history, and an automatically updated PR comment.

- Image source: `2b60950940f5edd06f2c1fa5c9a27df78259198d`.
- [Successful image publication](https://github.com/chrisknvidia/SkillEvaluator-ci-demo/actions/runs/39737144453).
- Image: `ghcr.io/chrisknvidia/skillevaluator-ci-demo@sha256:88047c35d1625325bb55fedef5953ff1caabe56383c2fa780a9bfa933d1752e4`.
- Reusable scan and publisher workflows: `5e3bb8b6af563c8069d9fcee2bfffe54bfa7731e`.
- Main commit: `9226a6a200b7d7adea558f8b817ffb5abbd9eeda`.
- PR commit: `bb8bd8130f99b20409f5148125adc18ea2af5de5`.

| Case | Inspected result | Evidence |
| --- | --- | --- |
| Main scan | 5/5 pass, 60 validator rows, 0 errors, 16 warnings; each skill scores 98.2/A | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39737381283), [report](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/runs/39737381283/1/) |
| PR scan | 5 pass, 1 fail, 72 validator rows, 2 errors; invalid skill scores 71.8/C | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39737400072), [report](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/runs/39737400072/1/) |
| Missing path | Configuration ERROR; zero validators; JSON, HTML and Markdown retained | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39736600644) |
| Missing LLM key | Configuration ERROR; zero validators; requested LLM mode recorded | [Run](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39736604141) |
| Main publication | History preparation and Pages deployment succeeded | [Publisher](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39737572513) |
| PR publication | History, Pages and automatic comment update succeeded | [Publisher](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/actions/runs/39737599230) |

The [same bot comment](https://github.com/chrisknvidia/skill-evaluator-consumer-demo/pull/1#issuecomment-6334583529)
was updated across PR commits: its identity stayed `6334583529`, exactly one marked
bot comment exists, and its current body identifies the final PR commit and run.
GitHub's returned rendered HTML contains a real six-row score table and readable
failure messages. Actual check annotations include both malformed-name failures,
the affected file and suggested fixes. No source line is invented when absent.

The real downloaded summaries were rendered by GitHub's Markdown API: 11 tables
for main and 13 for the PR, with readable findings and links only to published
files. JSON, HTML, Markdown and hosted receipt metadata agree on verdicts,
commits and runtime digest. The public site retains reports independently of the
14-day workflow artifact lifetime. [History](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/),
[latest main](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/main/latest/)
and [PR #1](https://chrisknvidia.github.io/skill-evaluator-consumer-demo/pr/1/)
provide browser entry points; each run/attempt has its own retained URL.
Historical runs were backfilled without replacing current aliases.

An independent edge-case and output-correctness review passed after fixes;
129 focused CI helper tests, Ruff, workflow validation and real GitHub rendering
checks passed. The first live output review caught broken Markdown table spacing,
escaped quote entities and links to files absent from hosted publication. Those
were fixed, rebuilt and verified through the fresh runs above. A subsequent
real-browser check found long runtime metadata overflowing narrow screens; the
CSS wrapping fix was verified using actual reports at 320, 390, 768 and 1440 pixels.
The two configuration-error tests used the preceding `6dbc7db` image, whose only
subsequent renderer change was that CSS wrapping rule.

Final hosted browser verification confirmed that both stable aliases resolve to
the exact final runs above. Desktop (1440px), mobile (390px), and expanded failure
details fit the viewport. All 13 unique report and JSON links returned HTTP 200;
there were no page JavaScript errors. The history includes both final runs.

Scope remains no-LLM Tier 1. Real credentialed LLM success, Tier 2, Tier 3 and
fork-origin PR publication were not tested. Missing-key rejection is not proof
of model-backed analysis. The older verification below records the initial
runtime, before this reporting extension.

## Initial runtime verification

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
