# CLAUDE.md - Plane Project Guide

This file provides guidance for Claude Code and other AI assistants working on the Plane codebase.

## Project Overview

Plane is an open-source project management tool built with:
- **Frontend**: React Router, TypeScript, Tailwind CSS, MobX
- **Backend**: Django REST Framework (Python 3.12)
- **Package Manager**: pnpm (monorepo with Turborepo)

## Repository Structure

```
plane/
├── apps/
│   ├── admin/          # Admin dashboard (Next.js-like)
│   ├── api/            # Django REST API (Python)
│   ├── live/           # Real-time collaboration service
│   ├── space/          # Public space viewer
│   ├── web/            # Main web application
│   └── proxy/          # Proxy configuration
├── packages/
│   ├── codemods/       # Code transformation utilities
│   ├── constants/      # Shared constants
│   ├── decorators/     # TypeScript decorators
│   ├── editor/         # Rich text editor
│   ├── hooks/          # React hooks
│   ├── i18n/           # Internationalization
│   ├── logger/         # Logging utilities
│   ├── propel/         # Animation library
│   ├── services/       # API service layer
│   ├── shared-state/   # MobX stores
│   ├── tailwind-config/# Tailwind configuration
│   ├── types/          # TypeScript types
│   ├── ui/             # UI component library
│   └── utils/          # Utility functions
└── deployments/        # Deployment configurations
```

## Quick Commands

### Development
```bash
pnpm dev                            # Start all dev servers (web:3000, admin:3001)
pnpm build                          # Build all packages and apps
pnpm turbo run <cmd> --filter=<pkg> # Target specific package/app
```

### Quality Checks
```bash
pnpm check                          # Run all checks (format, lint, types)
pnpm check:lint                     # ESLint across all packages
pnpm check:types                    # TypeScript type checking
pnpm check:format                   # Prettier format check
```

### Auto-fix
```bash
pnpm fix                            # Auto-fix format and lint issues
pnpm fix:lint                       # Fix ESLint issues only
pnpm fix:format                     # Fix Prettier issues only
```

### Testing
```bash
pnpm --filter=live test             # Run frontend tests (vitest)
cd apps/api && python run_tests.py  # Run backend tests (pytest)
```

### Backend Linting
```bash
cd apps/api
ruff check .                        # Run Ruff linter
ruff check --fix .                  # Auto-fix Ruff issues
python bin/custom_lint_rules.py .   # Run custom lint rules
```

## Code Style Guidelines

### TypeScript/JavaScript
- **ESLint 9**: Flat config with React, TypeScript, Prettier integration
- **Prettier**: Auto-formatting with Tailwind plugin
- Use `workspace:*` for internal package dependencies
- Use `catalog:` for external dependencies (managed in pnpm-workspace.yaml)
- Strict TypeScript mode enabled; all files must be fully typed
- No `any` types without explicit justification
- Prefix unused variables with `_` (e.g., `_unusedParam`)
- Use `@plane/logger` instead of `console.log`
- Build reusable components in `@plane/ui` with Storybook stories

### Python (Backend API)
- **Ruff**: Linting and formatting (configured in `apps/api/pyproject.toml`)
- **Ruff Rules**: E (pycodestyle), F (Pyflakes), UP006/UP035 (modern type annotations)
- Line length: 120 characters
- Docstrings: Google style convention
- Use PEP 585 generics (`list[int]` instead of `typing.List[int]`)
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.contract`, `@pytest.mark.smoke`

### Custom Python Lint Rules
Located at `apps/api/bin/custom_lint_rules.py`:

| Rule | Description |
|------|-------------|
| `no-dataclass` | Use Pydantic `BaseModel` instead of `@dataclass` |
| `no-typed-dict` | Use Pydantic `BaseModel` instead of `TypedDict` |
| `no-dict-tuple-return` | Return a `BaseModel` instead of `dict`/`tuple` |
| `modal-complexity` | Modal functions: max 50 lines, complexity <= 10 |
| `tool-name-string` | Use `ToolClass.name` instead of hardcoded strings |

Suppression: `# noqa: <rule>` or `# lint: ignore-<rule>` or `# noqa: custom-lint`

## Architecture Patterns

### Frontend State Management
- MobX stores in `packages/shared-state`
- Use `observer()` wrapper on components that read observables
- Services in `packages/services` handle API calls

### Backend API Structure
- Django REST Framework with ViewSets
- Serializers for all I/O validation
- Permission classes for access control
- Use `@transaction.atomic` for multi-step operations

### Component Development
- New UI components go in `@plane/ui`
- Include TypeScript prop types
- Create Storybook stories for visual testing
- Use `clsx` or `tailwind-merge` for conditional classes

## CI/CD Workflows

| Workflow | Purpose |
|----------|---------|
| `pull-request-build-lint-web-apps.yml` | Build, lint, type-check frontend |
| `pull-request-build-lint-api.yml` | Lint Python backend with Ruff |
| `custom-lint.yml` | Run custom Python lint rules (no-dataclass, no-typed-dict, etc.) |
| `pull-request-test-api.yml` | Run pytest (unit + contract tests) |
| `pull-request-test-frontend.yml` | Run vitest for frontend |
| `codeql.yml` | Security analysis |
| `codespell.yml` | Spell checking |
| `copyright-check.yml` | Copyright header verification |

## Common Pitfalls

### Frontend
- Always `await` async functions properly
- Wrap API calls in try-catch
- Use `observer()` on components reading MobX observables
- Clean up subscriptions in useEffect cleanup functions

### Backend
- Run `makemigrations` after model changes
- Use `select_related()` / `prefetch_related()` to avoid N+1 queries
- Never trust client input; validate with serializers
- Use `@transaction.atomic` for multi-step database operations

## Environment Setup

1. Clone and install dependencies:
   ```bash
   git clone https://github.com/makeplane/plane.git
   cd plane
   pnpm install
   ```

2. Set up environment:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Start development:
   ```bash
   # Frontend only
   pnpm dev

   # Full stack with Docker
   docker compose -f docker-compose-local.yml up
   ```

## PR Guidelines

- Default target branch: `preview`
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Run `pnpm check` before committing
- Include tests for new features
- Update documentation for API changes

## Testing Guidelines

### Frontend Testing
- **Framework**: Vitest
- **Location**: `apps/<app>/tests/` or alongside source files as `*.test.ts`
- Run tests: `pnpm --filter=<package> test`

### Backend Testing
- **Framework**: pytest with Django
- **Location**: `apps/api/plane/tests/` (organized by `unit/`, `contract/`, `smoke/`)
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.contract`, `@pytest.mark.smoke`
- Run tests: `cd apps/api && python run_tests.py`

### Test Coverage Expectations
- New features: Must include unit tests
- Bug fixes: Should include regression tests
- Backend: Aim for 90% coverage on new code

## Related Documentation

- [AGENTS.md](./AGENTS.md) - Detailed AI agent guidelines
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [Product Docs](https://docs.plane.so/) - User documentation
- [Developer Docs](https://developers.plane.so/) - Technical documentation
