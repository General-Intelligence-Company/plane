# Plane Project Overview

## Project Description

Plane is an open-source project management platform that unlocks customer value. It's built as a monorepo containing Next.js/React frontend applications and a Django/Python backend API.

## Repository Structure

```
plane/
├── apps/
│   ├── admin/        # Admin dashboard (Next.js)
│   ├── api/          # Backend API (Django/Python)
│   ├── live/         # Real-time collaboration server
│   ├── space/        # Public pages app (Next.js)
│   └── web/          # Main web application (Next.js)
├── packages/
│   ├── codemods/     # Code transformation utilities
│   ├── constants/    # Shared constants
│   ├── decorators/   # TypeScript decorators
│   ├── editor/       # Rich text editor components
│   ├── hooks/        # Shared React hooks
│   ├── i18n/         # Internationalization
│   ├── logger/       # Logging utilities
│   ├── propel/       # Workflow engine
│   ├── services/     # API service layer
│   ├── shared-state/ # MobX state management
│   ├── tailwind-config/ # Tailwind CSS configuration
│   ├── types/        # Shared TypeScript types
│   ├── typescript-config/ # TSConfig presets
│   ├── ui/           # Reusable UI components
│   └── utils/        # Shared utilities
├── deployments/      # Deployment configurations
└── docs/             # Documentation
```

## Technology Stack

### Frontend
- **Framework**: Next.js 14+ with React 18+
- **Language**: TypeScript (strict mode)
- **State Management**: MobX
- **Styling**: Tailwind CSS
- **Build System**: Turborepo with pnpm workspaces
- **Package Manager**: pnpm 10.x
- **Node Version**: 22.18.0+

### Backend
- **Framework**: Django with Django REST Framework
- **Language**: Python 3.12
- **Database**: PostgreSQL 14+
- **Cache/Queue**: Redis 6.2+
- **Task Queue**: Celery

## Development Commands

### Root-Level Commands (Frontend)

```bash
# Install dependencies
pnpm install

# Start all development servers
pnpm dev                    # Web: 3000, Admin: 3001

# Build all packages and apps
pnpm build

# Quality checks
pnpm check                  # Run all checks (format, lint, types)
pnpm check:lint             # ESLint only
pnpm check:types            # TypeScript only
pnpm check:format           # Prettier only

# Auto-fix issues
pnpm fix                    # Fix all issues
pnpm fix:lint               # Fix ESLint issues
pnpm fix:format             # Fix Prettier issues

# Target specific package/app
pnpm turbo run <command> --filter=<package>
```

### Backend Commands (apps/api)

```bash
cd apps/api

# Run with Docker (recommended)
docker compose -f docker-compose-local.yml up

# Run tests
python run_tests.py                           # All tests
python -m pytest -m unit                      # Unit tests only
python -m pytest -m contract                  # Contract tests only
python -m pytest -m smoke                     # Smoke tests only

# Linting
ruff check .                                  # Check for issues
ruff check --fix .                            # Auto-fix issues
ruff format .                                 # Format code

# Django commands
python manage.py makemigrations
python manage.py migrate
python manage.py shell
```

## Code Style Guidelines

### TypeScript/JavaScript
- Use `workspace:*` for internal package dependencies
- Use `catalog:` for external dependencies (defined in pnpm-workspace.yaml)
- All files must be fully typed (no implicit any)
- Use `camelCase` for variables/functions, `PascalCase` for components/types
- Prefix unused variables with `_`
- Use `@plane/logger` instead of console.log
- Use Tailwind CSS classes, no inline styles

### Python
- Line length: 120 characters
- Formatter: Ruff
- Import sorting: Ruff isort
- Docstrings: Google style
- Tests: Use pytest markers (`@pytest.mark.unit`, `@pytest.mark.contract`, `@pytest.mark.smoke`)

## Architecture Patterns

### Frontend
- **Components**: Build reusable components in `@plane/ui` with Storybook stories
- **Services**: API calls via `@plane/services`
- **State**: MobX stores in `@plane/shared-state`
- **Types**: Shared types in `@plane/types`

### Backend
- **Views**: Django REST Framework ViewSets
- **Serializers**: All I/O through serializers
- **Permissions**: Custom permission classes per endpoint
- **Async Tasks**: Celery for background jobs

## Testing

### Frontend
```bash
pnpm --filter=live test           # Run live app tests
pnpm --filter=@plane/codemods test # Run codemod tests
```

### Backend
```bash
cd apps/api
python run_tests.py                # Run all tests
python -m pytest -m unit -v        # Verbose unit tests
python -m pytest -k "test_name"    # Run specific test
```

## CI/CD Workflows

The repository uses GitHub Actions for CI/CD:

- **pull-request-build-lint-web-apps.yml**: Lint and build frontend apps
- **pull-request-build-lint-api.yml**: Lint Python backend
- **pull-request-test-api.yml**: Run backend tests
- **pull-request-test-frontend.yml**: Run frontend tests
- **build-branch.yml**: Build Docker images
- **codeql.yml**: Security analysis
- **codespell.yml**: Spell checking
- **copyright-check.yml**: License header verification

## Environment Setup

1. Copy `.env.example` to `.env` and configure
2. For frontend: `pnpm install`
3. For backend: Use Docker Compose or set up Python environment

## Key Configuration Files

- `eslint.config.mjs` - ESLint flat config for frontend
- `apps/api/pyproject.toml` - Ruff and Python project config
- `turbo.json` - Turborepo pipeline configuration
- `pnpm-workspace.yaml` - pnpm workspace definition
- `.husky/pre-commit` - Pre-commit hooks (lint-staged)

## PR Guidelines

- Target branch: `preview` (default)
- Use conventional commit format: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`
- Ensure all CI checks pass before requesting review
- Include tests for new features and bug fixes

## Related Documentation

- [AGENTS.md](./AGENTS.md) - AI agent development guidelines
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [SECURITY.md](./SECURITY.md) - Security policy
