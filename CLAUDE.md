# Plane - Project Overview

Plane is an open-source project management tool for tracking issues, running cycles, and managing product roadmaps.

## Architecture

### Monorepo Structure

```
plane/
├── apps/
│   ├── api/          # Django/Python backend (REST API)
│   ├── web/          # Next.js main web application
│   ├── admin/        # Admin dashboard
│   ├── space/        # Public project spaces
│   ├── live/         # Real-time collaboration service
│   └── proxy/        # Proxy service
├── packages/
│   ├── ui/           # Shared React components
│   ├── editor/       # Rich text editor
│   ├── services/     # API service layer
│   ├── types/        # Shared TypeScript types
│   ├── hooks/        # Shared React hooks
│   ├── utils/        # Utility functions
│   ├── constants/    # Shared constants
│   ├── i18n/         # Internationalization
│   ├── logger/       # Logging utilities
│   ├── shared-state/ # MobX state management
│   ├── decorators/   # TypeScript decorators
│   ├── codemods/     # Code transformation tools
│   ├── propel/       # Propel integration
│   └── tailwind-config/ # Tailwind CSS configuration
└── deployments/      # Docker and Kubernetes configs
```

### Tech Stack

- **Frontend**: React, Next.js, TypeScript, Tailwind CSS, MobX
- **Backend**: Django, Django REST Framework, Python 3.12
- **Database**: PostgreSQL
- **Cache**: Redis
- **Build**: pnpm workspaces, Turbo

## Development Commands

### Quick Start

```bash
# Install dependencies
pnpm install

# Start all dev servers
pnpm dev                              # web:3000, admin:3001

# Build all packages
pnpm build
```

### Quality Checks

```bash
# Run all checks (recommended before committing)
pnpm check                            # Format, lint, and type checks

# Individual checks
pnpm check:lint                       # ESLint
pnpm check:format                     # Prettier
pnpm check:types                      # TypeScript

# Auto-fix issues
pnpm fix                              # Fix all
pnpm fix:lint                         # Fix lint only
pnpm fix:format                       # Fix format only
```

### Testing

```bash
# Frontend tests
pnpm --filter=live test               # Vitest tests

# Backend tests
cd apps/api && python run_tests.py    # All tests
cd apps/api && python -m pytest -m unit  # Unit tests only
```

### Package-specific Commands

```bash
# Target specific package/app
pnpm turbo run <cmd> --filter=<pkg>

# Examples
pnpm turbo run build --filter=@plane/ui
pnpm --filter=@plane/ui storybook     # Storybook on port 6006
```

## Code Style

### TypeScript/JavaScript

- **ESLint**: Flat config (ESLint 9) with TypeScript, React, and accessibility rules
- **Prettier**: Auto-formatting with Tailwind plugin
- **Imports**: Use `workspace:*` for internal packages, `catalog:` for external
- **Types**: Strict mode; no `any` without justification
- **Naming**: `camelCase` for variables/functions, `PascalCase` for components/types
- **Unused vars**: Prefix with `_` (e.g., `_unusedParam`)

### Python (Backend)

- **Linter**: Ruff with E, F, UP006, UP035 rules
- **Line length**: 120 characters
- **Docstrings**: Google style convention
- **Target version**: Python 3.12

### Custom Lint Rules (Backend)

The backend has custom lint rules in `apps/api/scripts/custom_lint_rules.py`:

| Rule                   | Enforcement                                     |
| ---------------------- | ----------------------------------------------- |
| `no-dataclass`         | Use Pydantic BaseModel instead of @dataclass    |
| `no-typed-dict`        | Use Pydantic BaseModel instead of TypedDict     |
| `no-dict-tuple-return` | Return BaseModel instead of dict/tuple          |
| `modal-complexity`     | Modal functions: max 50 lines, complexity <= 10 |
| `tool-name-string`     | Use ToolClass.name instead of hardcoded strings |

Suppress with `# noqa: <rule>` or `# lint: ignore-<rule>`

## Pre-commit Hooks

Husky + lint-staged automatically runs on commit:

- Prettier formatting on all files
- ESLint on JS/TS files

## CI/CD Workflows

- **Frontend**: Build, lint, type check, format check, tests
- **Backend**: Ruff lint, unit tests, contract tests
- **Other**: CodeQL, codespell, copyright check

## Key Patterns

### State Management

MobX stores in `packages/shared-state`. Use reactive patterns with `observer()` HOC.

### API Services

Service classes in `packages/services`. One file per domain area.

### Components

Build reusable components in `@plane/ui` with Storybook stories.

### Error Handling

Use try-catch with proper types. Log via `@plane/logger`.

## Environment Variables

Copy `.env.example` to `.env` and configure. Key variables documented in the example files.

## Related Documentation

- [AGENTS.md](./AGENTS.md) - AI agent guidelines and checklists
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [Product docs](https://docs.plane.so/) - User documentation
- [Developer docs](https://developers.plane.so/) - API and self-hosting docs
