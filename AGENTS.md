# Repository Guidelines

## Project Structure & Module Organization
- Monorepo managed by `pnpm` workspaces.
- `apps/api` — FastAPI (Python 3.11+). Entry: `main_v2.py`; tests in `apps/api/tests/`.
- `apps/collector` — TypeScript Node (ESM). Source in `src/`; tests in `tests/`.
- `packages/` — shared configs/types (`shared-types`, `typescript-config`, `eslint-config`) and `scripts` (`race_collector`, `evaluation`).
- Reference assets: `docs/`, `examples/`, `data/`.
- Keep domain logic in `services/`; keep I/O and HTTP in the API layer.

## Build, Test, and Development Commands
- Install deps (root): `pnpm i`
- Dev (all apps via Turbo): `pnpm dev`
- Dev (one app): `pnpm -w -F @apps/collector dev` or `pnpm -w -F @apps/api dev`
- Build (workspace): `pnpm build`; per app: `pnpm -F @apps/collector build`
- Test (workspace): `pnpm test`
- Test per app: `pnpm -F @apps/collector test`, `pnpm -F @apps/api test`
- API direct (from `apps/api`): `uv run pytest -q`

## Coding Style & Naming Conventions
- TypeScript: 2-space indent, single quotes, semicolons, print width 120; ESM modules only.
- Naming: `camelCase` variables/functions; `PascalCase` types/classes. Tests: `*.test.ts` or `*.spec.ts`.
- Python: Black + Ruff (line length 88). `snake_case` functions; `PascalCase` classes.
- Keep files small and cohesive; colocate tests with each app.

## Testing Guidelines
- Node: Jest with ESM (`ts-jest`), 80% global coverage. Place tests under `apps/collector/tests/` mirroring `src/`. Run: `pnpm -F @apps/collector test`.
- Python: Pytest with asyncio and coverage. Place tests under `apps/api/tests/` (e.g., `tests/services/test_job_service.py`). Run: `uv run pytest -q`.

## Commit & Pull Request Guidelines
- Conventional Commits: `<type>(<scope>): <subject>`. Examples: `feat(api): add job endpoint`, `fix(collector): handle null payloads`.
- PRs: include a clear description, linked issues, repro steps, and test evidence (logs/coverage). Update docs when behavior changes.

## Security & Configuration
- Use `.env` files; never commit real keys. Copy from examples (e.g., `apps/collector/.env.example`, `apps/api/.env.example`).
- Gitleaks (`.gitleaks.toml`) is configured—keep secrets out of code and config.

## Agent-Specific Instructions
- When interacting with this repository's owner or contributors, respond in Korean (한국어로 답변). Keep replies concise and professional.

## API Guide
- 주요 API URL 및 사용법: [KRA_PUBLIC_API_GUIDE.md](apps/collector/KRA_PUBLIC_API_GUIDE.md)을(를) 참조하세요.

## Context7 Usage Triggers (short)
- Action/library options unclear (e.g., `actions/setup-node`, `codecov`, `pnpm/action-setup`, `codeql`, `gitleaks`).
- Framework specifics needed: FastAPI, pytest (asyncio/timeout/coverage), python-jose (JWT), httpx, redis-py.
- Version/deprecation checks: Actions v3→v4, runner image changes, major lib upgrades.
- Node CI strategy validation: ESM/ts-jest, pnpm workspaces, cache keys, lockfile behavior.

## ExecPlans

When writing complex features or significant refactors, use an ExecPlan (as described in .agent/PLANS.md) from design to implementation.
