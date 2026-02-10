# Agent Development Guide

This document provides guidelines for AI agents working on the Plane codebase. Follow these guidelines to ensure consistent, high-quality contributions.

## Quick Reference Commands

```bash
# Development
pnpm dev                           # Start all dev servers (web:3000, admin:3001)
pnpm build                         # Build all packages and apps
pnpm turbo run <cmd> --filter=<pkg> # Target specific package/app

# Quality Checks (run before committing)
pnpm check                         # Run all checks (format, lint, types)
pnpm check:lint                    # ESLint across all packages
pnpm check:types                   # TypeScript type checking
pnpm check:format                  # Prettier format check

# Auto-fix
pnpm fix                           # Auto-fix format and lint issues
pnpm fix:lint                      # Fix ESLint issues only
pnpm fix:format                    # Fix Prettier issues only

# Testing
pnpm --filter=live test            # Run frontend tests (vitest)
cd apps/api && python run_tests.py # Run backend tests (pytest)

# Storybook
pnpm --filter=@plane/ui storybook  # Start Storybook on port 6006
```

## Code Style Requirements

### TypeScript/JavaScript
- **Imports**: Use `workspace:*` for internal packages, `catalog:` for external deps
- **TypeScript**: Strict mode enabled; all files must be fully typed
- **Formatting**: Prettier with Tailwind plugin (`pnpm fix:format`)
- **Linting**: ESLint 9 with flat config; max warnings vary by package
- **Naming Conventions**:
  - `camelCase` for variables and functions
  - `PascalCase` for components, types, and interfaces
  - Prefix unused variables with `_` (e.g., `_unusedParam`)
- **Error Handling**: Use try-catch with proper error types; log errors via `@plane/logger`
- **State Management**: MobX stores in `packages/shared-state`; use reactive patterns
- **Components**: Build reusable components in `@plane/ui` with Storybook stories

### Python (Backend API)
- **Linting/Formatting**: Ruff (configured in `apps/api/pyproject.toml`)
- **Custom Lint Rules**: Run `python apps/api/bin/custom_lint_rules.py <files>` (see below)
- **Line Length**: 120 characters maximum
- **Docstrings**: Google style convention
- **Imports**: Sorted by Ruff isort rules; use PEP 585 generics (`list[int]` not `List[int]`)
- **Tests**: Use pytest markers (`@pytest.mark.unit`, `@pytest.mark.contract`, `@pytest.mark.smoke`)

#### Custom Python Lint Rules

The project enforces additional coding standards via `apps/api/bin/custom_lint_rules.py`:

| Rule | What it enforces | Fix |
|------|-----------------|-----|
| `no-dataclass` | No `@dataclass` usage | Use Pydantic `BaseModel` |
| `no-typed-dict` | No `TypedDict` usage | Use Pydantic `BaseModel` |
| `no-dict-tuple-return` | No `dict`/`tuple` return types | Return a `BaseModel` |
| `modal-complexity` | Modal functions: ≤50 lines, complexity ≤10 | Split into smaller functions |
| `tool-name-string` | No hardcoded tool name strings | Use `ToolClass.name` |

**How to run:**
```bash
cd apps/api
python bin/custom_lint_rules.py .           # Check all files
python bin/custom_lint_rules.py plane/api/  # Check specific directory
```

**Suppression (per-line):**
- `# noqa: <rule>` - Suppress specific rule
- `# lint: ignore-<rule>` - Alternative suppression syntax
- `# noqa: custom-lint` - Suppress all custom rules
- `# noqa` - Suppress all checks on line

## Testing Requirements

### Before Submitting Changes

1. **Run all quality checks**:
   ```bash
   pnpm check  # Must pass with no errors
   ```

2. **Run relevant tests**:
   - Frontend changes: `pnpm --filter=<package> test` (if tests exist)
   - Backend changes: `cd apps/api && python run_tests.py`

3. **Build verification**:
   ```bash
   pnpm build  # Must complete successfully
   ```

### Test Coverage Expectations
- **New features**: Must include unit tests
- **Bug fixes**: Should include regression tests
- **Backend**: Aim for 90% coverage on new code
- **Frontend**: Test critical business logic and user interactions

### Test File Locations
- Frontend: `apps/<app>/tests/` or alongside source files as `*.test.ts`
- Backend: `apps/api/plane/tests/` (organized by `unit/`, `contract/`, `smoke/`)

## Pre-commit Checklist

Before creating a commit, ensure:

- [ ] `pnpm check` passes (lint, format, types)
- [ ] `pnpm build` completes successfully
- [ ] All new code has proper TypeScript types
- [ ] No `any` types without explicit justification
- [ ] New features have corresponding tests
- [ ] API changes update relevant serializers and tests
- [ ] Copyright headers present on new files
- [ ] No console.log statements (use `@plane/logger` instead)
- [ ] No hardcoded secrets or credentials
- [ ] Environment variables documented if new ones added

## Code Review Checklist

When reviewing or self-reviewing code:

### General
- [ ] Code follows the established patterns in the codebase
- [ ] No duplicate code that could be extracted to shared packages
- [ ] Error handling is comprehensive
- [ ] Edge cases are considered

### Frontend Specific
- [ ] Components are properly typed with TypeScript
- [ ] No inline styles (use Tailwind classes)
- [ ] Accessibility considerations (labels, ARIA attributes)
- [ ] Responsive design for mobile/tablet
- [ ] MobX observables are properly decorated
- [ ] useEffect dependencies are correct
- [ ] No memory leaks (cleanup in useEffect)

### Backend Specific
- [ ] API endpoints have proper permissions
- [ ] Database queries are optimized (no N+1 queries)
- [ ] Serializers validate input properly
- [ ] Migrations are reversible when possible
- [ ] No raw SQL without proper escaping

## Common Pitfalls to Avoid

### TypeScript/JavaScript
1. **Forgetting `await`**: Always check async functions are properly awaited
2. **Missing error handling**: Wrap API calls in try-catch
3. **Circular imports**: Be careful with cross-package imports
4. **MobX reactivity**: Use `observer()` on components that read observables
5. **Memory leaks**: Clean up subscriptions and event listeners

### Python
1. **Missing migrations**: Always run `makemigrations` after model changes
2. **N+1 queries**: Use `select_related()` and `prefetch_related()`
3. **Serializer validation**: Don't trust client input
4. **Transaction safety**: Use `@transaction.atomic` for multi-step operations

### General
1. **Large commits**: Keep changes focused and atomic
2. **Missing tests**: New features should have test coverage
3. **Undocumented APIs**: Update API documentation for changes
4. **Breaking changes**: Flag any backwards-incompatible changes

## Verifying Changes Work Correctly

### Frontend Changes
1. Start dev server: `pnpm dev`
2. Test in browser at http://localhost:3000
3. Check browser console for errors
4. Test on different screen sizes
5. Verify no regressions in related features

### Backend Changes
1. Start API with Docker: `docker compose -f docker-compose-local.yml up`
2. Test endpoints via browser or API client
3. Check Django admin for model changes
4. Verify database migrations work both up and down

### Full Stack Changes
1. Start all services: Docker + `pnpm dev`
2. Test complete user flows end-to-end
3. Check network tab for API errors
4. Verify data persistence

## Pull Request Guidelines

### PR Title Format
Use conventional commit format:
- `feat: Add new feature description`
- `fix: Resolve bug description`
- `refactor: Improve code structure`
- `docs: Update documentation`
- `test: Add missing tests`
- `chore: Update dependencies`

### PR Description Template
```markdown
## Summary
Brief description of what this PR does.

## Changes
- Bullet list of specific changes made

## Testing
- How was this tested?
- Any specific scenarios to verify?

## Screenshots (if UI changes)
Before/After screenshots if applicable

## Checklist
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

### Branch Naming
- Feature: `feat/short-description`
- Fix: `fix/issue-number-description`
- Refactor: `refactor/area-description`

### Target Branch
- Default branch is `preview`
- Always create PRs against `preview` unless instructed otherwise

## Package-Specific Guidelines

### @plane/ui
- All new components need Storybook stories
- Use `clsx` or `tailwind-merge` for conditional classes
- Export components from `index.ts`
- Include TypeScript prop types

### @plane/services
- One service file per domain area
- Use consistent error handling patterns
- Include request/response types

### apps/api
- Follow Django REST Framework patterns
- Use serializers for all I/O
- Include permission classes
- Write tests for all endpoints

## Getting Help

- Check existing code for patterns
- Read [CLAUDE.md](./CLAUDE.md) for detailed project information
- Review [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines
- Search GitHub issues for similar problems
- Ask in Discord for community support
