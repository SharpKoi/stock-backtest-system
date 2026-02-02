---
name: github-ci-cd
description: Configure the github actions for CI/CD. Use this skill when setting up Github CI/CD pipeline.
---

This skill defines the workflow and decision-making process for configuring CI/CD pipelines using GitHub Actions. It focuses on the process to follow and the edge cases to handle — not on YAML syntax or language-specific boilerplate, which you already know.

---

## Workflow

### Phase 1: Project Analysis

Before writing any workflow file, gather context by reading the project. Use the Explore agent or file-reading tools to check the following:

1. **Project manifest files** — Identify language, runtime, package manager, and dependency lock files.
2. **Existing scripts** — Look for test, lint, build, format, and deploy scripts in `package.json`, `Makefile`, `pyproject.toml`, `Taskfile.yml`, `justfile`, etc. Prefer calling these existing scripts rather than inlining raw commands in the workflow.
3. **Existing workflows** — Read everything under `.github/workflows/` and `.github/actions/`. Understand existing conventions (naming, structure, reusable workflows, composite actions) so that new workflows are consistent. Avoid creating duplicate workflows.
4. **Monorepo detection** — Check if the project contains multiple packages, services, or apps (e.g., `packages/`, `apps/`, `services/` directories, workspace config in `package.json`, `pnpm-workspace.yaml`, Cargo workspace in `Cargo.toml`, Go workspace). This significantly affects workflow design.
5. **Dockerfile / docker-compose** — Determines whether Docker build/push is part of the pipeline.
6. **Branch and tag conventions** — Check the default branch (`main` vs `master`), and look at existing tags or release conventions (`v*`, semver).
7. **Environment config** — Look for `.env.example`, environment-specific config files, or `infrastructure/` directories that hint at deployment targets.

### Phase 2: Clarify with the User

After analysis, ask the user about anything that cannot be inferred. Key questions:

- **Trigger events**: push, pull_request, release, schedule, workflow_dispatch?
- **Target branches**: Which branches should trigger CI? Should PRs against specific branches trigger it?
- **Required checks**: tests, lint, type-check, build, security scan?
- **CD scope**: Is deployment needed? If so, target environment(s) and strategy (auto-deploy vs manual approval)?
- **Secrets**: Any API keys, tokens, or credentials needed? Are they already configured in GitHub Secrets?
- **Workflow separation**: One combined workflow or separate CI/CD files?

Do not ask about things you can confidently infer from the project analysis. Only ask when there is genuine ambiguity.

### Phase 3: Write the Workflow

Generate workflow files under `.github/workflows/`. After writing, briefly explain the key design decisions you made and any assumptions.

---

## Decision Guidelines

### When to Split Workflows

- **Split CI and CD** when they have different triggers (e.g., CI on every PR, CD only on push to `main` or on release).
- **Split by concern** in monorepos: consider per-package workflows with path filters, or a single workflow with conditional jobs.
- **Keep combined** when the pipeline is simple and linear (e.g., test → build → deploy in a single small project).

### When to Use Matrix Builds

- When the project explicitly supports multiple runtime versions (e.g., a library targeting Node 18/20/22).
- When cross-platform compatibility matters (e.g., a CLI tool that runs on linux/macos/windows).
- **Do not** default to matrix builds for application projects that only run on one version in production — it adds cost and time for no benefit.

### When to Use GitHub Environments

- When deployments need protection rules (required reviewers, wait timers).
- When different deployment targets (staging, production) need different secrets.
- When you want deployment history and status visible in the GitHub UI.
- **Do not** use environments for simple CI-only workflows.

### When to Use Reusable Workflows vs Composite Actions

- **Reusable workflows** (`workflow_call`): for sharing entire job definitions across repositories or within a monorepo. They run as separate workflow runs and support `secrets: inherit`.
- **Composite actions**: for sharing a sequence of steps within a single repository. They're simpler but cannot define services, matrix strategies, or multi-job pipelines.

### Concurrency Control

- Always add concurrency groups for CI workflows to cancel redundant runs on the same branch/PR.
- For CD/deployment workflows, set `cancel-in-progress: false` — interrupting a deployment mid-way can leave the system in a broken state.
- Use `${{ github.workflow }}-${{ github.ref }}` as the concurrency group pattern.

---

## Edge Cases and Gotchas

### Fork PRs and Secrets

- **`pull_request` events from forks do NOT have access to repository secrets.** Workflows that require secrets (e.g., for integration tests against an external API) will fail silently or error.
- Solutions:
  - Split the workflow: run secret-free checks (lint, unit tests) on `pull_request`, and run secret-dependent checks only on `push` to branches within the repo.
  - Use environment-based approvals for fork PRs that need secrets.
- See **"Fork PRs — Split Workflow"** in `edge-case-examples.md` for a concrete split-workflow approach.

### GITHUB_TOKEN Limitations

- `GITHUB_TOKEN` cannot trigger other workflows. If workflow A creates a commit or release using `GITHUB_TOKEN`, workflow B that listens for those events will NOT be triggered.
- Workaround: use a GitHub App token (e.g., via `actions/create-github-app-token`) or a Personal Access Token stored in secrets.
- `GITHUB_TOKEN` permissions differ between `pull_request` (read-only by default) and `push` events. Always declare explicit `permissions:` blocks.
- See **"GITHUB_TOKEN — Triggering Downstream Workflows"** in `edge-case-examples.md` for a BAD vs GOOD comparison using a GitHub App token.

### Monorepo Path Filtering

- Use `paths:` filters to avoid running all workflows on every change. See **"Monorepo — Trigger-Level Path Filter"** in `edge-case-examples.md` for a basic example.
- **Gotcha**: `paths` filtering does not work with `workflow_dispatch` or `schedule` triggers — those always run regardless of path filters.
- **Gotcha**: If a required status check uses path filtering, PRs that don't match the paths will be blocked because the check never runs. Solutions:
  - Use `paths-ignore` instead of `paths`.
  - Use `dorny/paths-filter` action inside the workflow and use `if:` conditions on jobs instead of trigger-level `paths`.
  - Configure the branch protection rule to not require that specific check.
- See **"Monorepo — dorny/paths-filter for Required Checks"** in `edge-case-examples.md` for the recommended workaround.

### Checkout Depth and Git History

- `actions/checkout@v4` defaults to `fetch-depth: 1` (shallow clone). This is fine for most CI tasks.
- If the workflow needs full git history (e.g., for changelog generation, version calculation with `git describe`, or diff-based analysis), set `fetch-depth: 0`.
- For PRs where you only need the diff, `fetch-depth: 2` is sufficient.
- See **"Checkout Depth — Full History for Version Calculation"** in `edge-case-examples.md` for a `git describe` example.

### Artifact Handling Between Jobs

- Artifacts uploaded in one job are available to other jobs in the **same workflow run** via `actions/download-artifact`.
- Artifacts have a default retention of 90 days. Set `retention-days` explicitly for large artifacts to avoid storage costs.
- **Gotcha**: Artifact names must be unique within a workflow run. In matrix builds, include the matrix values in the artifact name (e.g., `build-output-node-20-linux`).
- **Gotcha**: `actions/upload-artifact@v4` / `download-artifact@v4` (v4) are NOT compatible with the v3 versions. Don't mix them — use v4 consistently.
- See **"Artifacts — Unique Names in Matrix Builds"** in `edge-case-examples.md` for the naming pattern.

### Timeouts

- GitHub Actions has a default job timeout of 6 hours. Always set an explicit `timeout-minutes` on jobs to fail fast and avoid burning minutes.
- For individual steps that might hang (e.g., integration tests, network calls), set step-level `timeout-minutes`.
- See **"Timeouts — Job-Level and Step-Level"** in `edge-case-examples.md` for both patterns.

### Docker Build Caching

- Use GitHub Actions cache (`cache-from: type=gha`, `cache-to: type=gha,mode=max`) for Docker builds.
- **Gotcha**: GHA cache has a 10GB limit per repository. If multiple workflows push Docker cache, they compete for space. Consider using registry-based caching (`type=registry`) for large images.
- **Gotcha**: Multi-platform builds (linux/amd64 + linux/arm64) require QEMU setup via `docker/setup-qemu-action`. These builds are significantly slower.
- See **"Docker — Registry-Based Cache"** and **"Docker — Multi-Platform Build with QEMU"** in `edge-case-examples.md` for both patterns.

### Conditional Deployment

- Use `if:` to guard deployment jobs. See **"Conditional Deployment — Guard with `if:`"** in `edge-case-examples.md`.
- **Gotcha**: When using `needs:` with `if:`, a skipped job causes all downstream jobs that depend on it to also be skipped. Use `if: always() && needs.build.result == 'success'` if you need to run a job regardless of whether an optional upstream job was skipped.
- See **"Conditional Deployment — Handling Skipped Upstream Jobs"** in `edge-case-examples.md` for the `always()` workaround.

### Self-Hosted Runners

- If the user mentions self-hosted runners, always ask about the runner labels and OS.
- Self-hosted runners do NOT get a clean environment by default. Add cleanup steps or use ephemeral runners.
- Docker-in-Docker and service containers may not work on all self-hosted runner configurations.
- Security: self-hosted runners on public repositories are a security risk — anyone can submit a PR that runs code on the runner.
- See **"Self-Hosted Runners — Workspace Cleanup"** in `edge-case-examples.md` for a cleanup step pattern.

### Scheduled Workflows (cron)

- Cron schedules use UTC timezone.
- **Gotcha**: Scheduled workflows only run on the default branch. If the workflow file only exists on a feature branch, the schedule will not trigger.
- **Gotcha**: GitHub may disable scheduled workflows on repositories with no activity for 60 days. The repository owner will receive an email notification.
- See **"Scheduled Workflows — Nightly Dependency Audit"** in `edge-case-examples.md` for a cron example.

### `pull_request` vs `pull_request_target`

- `pull_request`: runs in the context of the merge commit, with read-only permissions. Safe for untrusted code.
- `pull_request_target`: runs in the context of the **base branch**, with write permissions. Useful for labeling, commenting, but **dangerous if you checkout the PR head and run its code** — this gives untrusted code write access.
- Rule: if using `pull_request_target`, never `actions/checkout` the PR's head ref without explicit review controls.
- See **"`pull_request_target` — Safe Usage (Labeling)"** and **"`pull_request_target` — Dangerous Anti-Pattern"** in `edge-case-examples.md` for a safe vs dangerous comparison.

### Required Status Checks and Job Names

- Branch protection rules reference status checks by **job name** (or the `name:` of the workflow + job). If you rename a job, the branch protection rule will break.
- When designing workflows, choose stable, descriptive job names and inform the user that these names are referenced in branch protection settings.
- See **"Status Checks — Job Name Composition"** in `edge-case-examples.md` to understand how workflow name + job key form the check name.

### Permissions and OIDC

- For cloud deployments (AWS, GCP, Azure), prefer OIDC (`id-token: write`) over long-lived credentials. This avoids storing cloud provider secrets in GitHub.
- **Gotcha**: OIDC requires the cloud provider to be configured with a trust policy for the GitHub Actions identity. Remind the user to set this up on the cloud provider side.
- See **"OIDC — AWS Deployment Without Long-Lived Secrets"** in `edge-case-examples.md` for an AWS OIDC example.

### `actions/cache` Scope

- Cache is scoped to the branch. A PR branch can read caches from the base branch, but not from other PR branches.
- The default branch's cache is available to all branches. Structure your caching strategy so the default branch populates the cache.
- Cache keys should include the lock file hash (e.g., `hashFiles('**/package-lock.json')`) to invalidate on dependency changes.
- See **"`actions/cache` — Fallback Keys"** in `edge-case-examples.md` for a `restore-keys` pattern that enables partial cache hits.

---

## Checklist Before Finishing

Before presenting the workflow to the user, verify:

- [ ] `permissions:` is explicitly declared with minimum required permissions.
- [ ] `concurrency:` is set appropriately (cancel-in-progress for CI, not for CD).
- [ ] `timeout-minutes:` is set on jobs that could hang.
- [ ] Dependencies are cached (either via setup-action built-in cache or `actions/cache`).
- [ ] Secrets are referenced via `${{ secrets.* }}`, never hardcoded.
- [ ] Action versions are pinned to major version tags (e.g., `@v4`).
- [ ] Job and step names are descriptive.
- [ ] Path filters are used if the repository is a monorepo.
- [ ] The workflow file name is descriptive and consistent with existing conventions.
- [ ] If CD is included, deployment jobs are guarded by appropriate conditions (`if:`, `environment:`, branch filters).
