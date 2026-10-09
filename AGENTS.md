# Repository Guidelines

## Project Structure & Module Organization
- Monorepo managed by `pnpm` workspaces.
- `apps/api` — FastAPI (Python 3.13+). Entry: `main_v2.py`; tests in `apps/api/tests/`. 데이터 수집/강화도 API 엔드포인트로 통합 (Supabase DB 저장).
- `packages/` — shared configs/types (`shared-types`, `typescript-config`, `eslint-config`) and `scripts` (`evaluation`, `prompt_improvement`).
- Reference assets: `docs/`, `examples/`, `data/`.
- Keep domain logic in `services/`; keep I/O and HTTP in the API layer.

## Build, Test, and Development Commands
- Install deps (root): `pnpm i`
- Dev (all apps via Turbo): `pnpm dev`
- Dev (API): `pnpm -w -F @apps/api dev`
- Build (workspace): `pnpm build`
- Test (workspace): `pnpm test`
- Test API: `pnpm -F @apps/api test`
- API direct (from `apps/api`): `uv run pytest -q`

## Coding Style & Naming Conventions
- TypeScript: 2-space indent, single quotes, semicolons, print width 120; ESM modules only.
- Naming: `camelCase` variables/functions; `PascalCase` types/classes. Tests: `*.test.ts` or `*.spec.ts`.
- Python: Black + Ruff (line length 88). `snake_case` functions; `PascalCase` classes.
- Keep files small and cohesive; colocate tests with each app.

## Testing Guidelines
- Python: Pytest with asyncio and coverage. Place tests under `apps/api/tests/` (e.g., `tests/services/test_job_service.py`). Run: `uv run pytest -q`.

## Commit & Pull Request Guidelines
- Conventional Commits: `<type>(<scope>): <subject>`. Examples: `feat(api): add job endpoint`, `fix(collector): handle null payloads`.
- PRs: include a clear description, linked issues, repro steps, and test evidence (logs/coverage). Update docs when behavior changes.

## Security & Configuration
- Use `.env` files; never commit real keys. Copy from examples (e.g., `apps/api/.env.template`).
- Gitleaks (`.gitleaks.toml`) is configured—keep secrets out of code and config.

## Agent-Specific Instructions
- When interacting with this repository's owner or contributors, respond in Korean (한국어로 답변). Keep replies concise and professional.

## API Guide
- 주요 API URL 및 사용법: KRA_PUBLIC_API_GUIDE.md를 참조하세요.

## Context7 Usage Triggers (short)
- Action/library options unclear (e.g., `actions/setup-node`, `codecov`, `pnpm/action-setup`, `codeql`, `gitleaks`).
- Framework specifics needed: FastAPI, pytest (asyncio/timeout/coverage), python-jose (JWT), httpx, redis-py.
- Version/deprecation checks: Actions v3→v4, runner image changes, major lib upgrades.
- Node CI strategy validation: ESM/ts-jest, pnpm workspaces, cache keys, lockfile behavior.

## ExecPlans

When writing complex features or significant refactors, use an ExecPlan (as described in .agent/PLANS.md) from design to implementation.

## Research Goal Operations
- The target is 70% race-level exact success for one unordered three-horse prediction, using only pre-race information and the complete frozen race universe. Do not substitute top-k, portfolio, retrospective proxy, or skipped-race subset metrics.
- When research becomes difficult, consolidate the evidence and open questions and consult the user's ChatGPT Pro model through the authorized browser. Wait for the completed response without stopping generation or imposing a short response timeout. If access is unavailable, record the blocker and never claim a consultation occurred.
- For the owner's ongoing research request, commit, push, and merge validated improvements in small increments after tests and required checks pass. Isolate unrelated working-tree changes and never force a failing merge.
