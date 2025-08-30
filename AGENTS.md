# Repository Guidelines

## Project Structure & Modules
- apps/api: FastAPI service (Python 3.11+, uv, pytest). Entry: `main_v2.py`, tests in `apps/api/tests`.
- apps/collector: TypeScript Node service (ESM). Sources in `src/`, tests in `tests/`.
- packages/shared-types, typescript-config, eslint-config: Shared TS configs and types.
- packages/scripts: Data collection/evaluation scripts (`race_collector`, `evaluation`).
- docs, examples, data: Reference material and sample assets.

## Build, Test, Run
- Install: `pnpm i` (workspace root).
- Dev (all): `pnpm dev` (Turbo runs per app).
- Dev (one app): `pnpm -w -F @apps/collector dev` or `pnpm -w -F @apps/api dev`.
- Build: `pnpm build` (Turbo). Per app: `pnpm -F @apps/collector build`.
- Test: `pnpm test` (workspace). Per app: `pnpm -F @apps/collector test`, `pnpm -F @apps/api test` (runs `uv run pytest`).
- Lint/Typecheck: `pnpm lint`, `pnpm -F @repo/shared-types typecheck`.

## Coding Style & Naming
- TypeScript: 2‑space indent, single quotes, semicolons, print width 120 (Prettier). ESM modules, `camelCase` vars, `PascalCase` types/classes. Tests: `*.test.ts|*.spec.ts`.
- Python (apps/api): Black + Ruff (line length 88), `snake_case` functions, `PascalCase` classes. Keep pure functions in `services/`, I/O at API layer.
- Keep files small and cohesive; colocate tests with `tests/` (Py) or under `tests/` (TS).

## Testing Guidelines
- Node: Jest configured with ESM (`ts-jest`). Run `pnpm -F @apps/collector test`. Coverage collection is set; thresholds at 70% global.
- Python: Pytest with asyncio and coverage. Run `pnpm -F @apps/api test` or `uv run pytest -q` from `apps/api`.
- Name tests meaningfully, mirror source paths (e.g., `tests/services/test_job_service.py`).

## Commit & PR Guidelines
- Conventional Commits: `<type>(<scope>): <subject>` (see `.gitmessage`). Types: feat, fix, docs, refactor, test, chore, etc.
- PRs: clear description, linked issues, steps to reproduce, and test evidence (logs, coverage). Update docs when behavior changes.

## Security & Config
- Secrets: use `.env` files; never commit real keys. Gitleaks config present (`.gitleaks.toml`).
- Local env: copy provided `.env.example` where available (e.g., `apps/collector/.env.example`).
