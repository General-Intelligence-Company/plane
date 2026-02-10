#!/usr/bin/env python3
"""
Custom lint rules for the Plane backend.

This script enforces project-specific coding standards beyond what Ruff provides.

Rules:
- no-dataclass: Disallow @dataclass usage; use Pydantic BaseModel instead
- no-typed-dict: Disallow TypedDict usage; use Pydantic BaseModel instead
- no-dict-tuple-return: Disallow explicit dict/tuple return annotations; return a BaseModel
- modal-complexity: Modal functions must be <= 50 non-empty lines and cyclomatic complexity <= 10
- tool-name-string: Disallow hardcoded tool name strings; use ToolClass.name instead

Suppression mechanisms:
- # lint: ignore-<rule> (per-line suppression)
- # noqa: <rule> (per-line suppression)
- # noqa: custom-lint (per-line suppression for all custom rules)
- # noqa with no specific codes suppresses all custom lint checks on that line

Usage:
    python scripts/custom_lint_rules.py [files...]
    python scripts/custom_lint_rules.py  # checks all Python files in plane/
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import NamedTuple

# Legacy allowlist for paths that skip certain rules
LEGACY_ALLOWLIST: dict[str, set[str]] = {
    # Example: "plane/legacy_module/": {"no-dataclass", "no-typed-dict"},
}


class LintError(NamedTuple):
    """Represents a lint error."""

    file: str
    line: int
    rule: str
    message: str


def get_line_content(source_lines: list[str], line_num: int) -> str:
    """Get the content of a specific line (1-indexed)."""
    if 1 <= line_num <= len(source_lines):
        return source_lines[line_num - 1]
    return ""


def is_suppressed(line_content: str, rule: str) -> bool:
    """Check if a rule is suppressed on a given line."""
    # Check for noqa without any codes (suppresses all)
    if re.search(r"#\s*noqa\s*$", line_content):
        return True
    # Check for noqa: custom-lint (suppresses all custom rules)
    if re.search(r"#\s*noqa:\s*custom-lint", line_content, re.IGNORECASE):
        return True
    # Check for lint: ignore-<rule>
    if re.search(rf"#\s*lint:\s*ignore-{rule}", line_content, re.IGNORECASE):
        return True
    # Check for noqa: <rule>
    if re.search(rf"#\s*noqa:\s*{rule}", line_content, re.IGNORECASE):
        return True
    return False


def is_in_allowlist(file_path: str, rule: str) -> bool:
    """Check if a file is in the legacy allowlist for a specific rule."""
    for pattern, rules in LEGACY_ALLOWLIST.items():
        if pattern in file_path and rule in rules:
            return True
    return False


def calculate_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Calculate cyclomatic complexity of a function."""
    complexity = 1  # Base complexity

    for child in ast.walk(node):
        # Branching statements
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        # Exception handlers
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        # Boolean operators (and, or)
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        # Comprehensions with conditionals
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            for generator in child.generators:
                complexity += len(generator.ifs)
        # Match statements (Python 3.10+)
        elif isinstance(child, ast.Match):
            complexity += len(child.cases) - 1
        # Assert statements
        elif isinstance(child, ast.Assert):
            complexity += 1
        # Ternary expressions
        elif isinstance(child, ast.IfExp):
            complexity += 1

    return complexity


def count_non_empty_lines(node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]) -> int:
    """Count non-empty, non-comment lines in a function body."""
    if not node.body:
        return 0

    start_line = node.body[0].lineno
    end_line = node.end_lineno or start_line

    count = 0
    for i in range(start_line - 1, end_line):
        if i < len(source_lines):
            line = source_lines[i].strip()
            if line and not line.startswith("#"):
                count += 1

    return count


def has_modal_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function has a Modal-related decorator."""
    modal_decorators = {"app.function", "app.local_entrypoint", "app.cls", "modal.function", "modal.method"}

    for decorator in node.decorator_list:
        decorator_name = ""
        if isinstance(decorator, ast.Name):
            decorator_name = decorator.id
        elif isinstance(decorator, ast.Attribute):
            parts = []
            current = decorator
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            decorator_name = ".".join(reversed(parts))
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                parts = []
                current = decorator.func
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                decorator_name = ".".join(reversed(parts))
            elif isinstance(decorator.func, ast.Name):
                decorator_name = decorator.func.id

        if decorator_name in modal_decorators:
            return True

    return False


class LintVisitor(ast.NodeVisitor):
    """AST visitor that checks for lint rule violations."""

    def __init__(self, file_path: str, source: str):
        self.file_path = file_path
        self.source = source
        self.source_lines = source.splitlines()
        self.errors: list[LintError] = []

    def add_error(self, line: int, rule: str, message: str) -> None:
        """Add a lint error if not suppressed."""
        line_content = get_line_content(self.source_lines, line)
        if not is_suppressed(line_content, rule) and not is_in_allowlist(self.file_path, rule):
            self.errors.append(LintError(self.file_path, line, rule, message))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check for dataclass and TypedDict usage."""
        # Check for @dataclass decorator
        for decorator in node.decorator_list:
            decorator_name = ""
            if isinstance(decorator, ast.Name):
                decorator_name = decorator.id
            elif isinstance(decorator, ast.Attribute):
                decorator_name = decorator.attr
            elif isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name):
                    decorator_name = decorator.func.id
                elif isinstance(decorator.func, ast.Attribute):
                    decorator_name = decorator.func.attr

            if decorator_name == "dataclass":
                self.add_error(
                    decorator.lineno,
                    "no-dataclass",
                    "@dataclass is not allowed. Use Pydantic BaseModel instead.",
                )

        # Check for TypedDict base class
        for base in node.bases:
            base_name = ""
            if isinstance(base, ast.Name):
                base_name = base.id
            elif isinstance(base, ast.Attribute):
                base_name = base.attr

            if base_name == "TypedDict":
                self.add_error(
                    node.lineno,
                    "no-typed-dict",
                    "TypedDict is not allowed. Use Pydantic BaseModel instead.",
                )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions."""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definitions."""
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check a function for rule violations."""
        # Check return type annotation for dict/tuple
        if node.returns:
            self._check_return_annotation(node.returns, node.lineno)

        # Check modal function complexity
        if has_modal_decorator(node):
            line_count = count_non_empty_lines(node, self.source_lines)
            if line_count > 50:
                self.add_error(
                    node.lineno,
                    "modal-complexity",
                    f"Modal function is too long ({line_count} lines > 50).",
                )

            complexity = calculate_complexity(node)
            if complexity > 10:
                self.add_error(
                    node.lineno,
                    "modal-complexity",
                    f"Modal function complexity too high ({complexity} > 10).",
                )

    def _check_return_annotation(self, annotation: ast.expr, line: int) -> None:
        """Check if return annotation uses forbidden dict/tuple types."""
        if isinstance(annotation, ast.Name):
            if annotation.id in ("dict", "tuple"):
                self.add_error(
                    line,
                    "no-dict-tuple-return",
                    "Explicit dict/tuple return annotations are not allowed. Return a Pydantic BaseModel instead.",
                )
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id in ("dict", "tuple", "Dict", "Tuple"):
                    self.add_error(
                        line,
                        "no-dict-tuple-return",
                        "Explicit dict/tuple return annotations are not allowed. Return a Pydantic BaseModel instead.",
                    )

    def visit_Call(self, node: ast.Call) -> None:
        """Check for hardcoded tool name strings."""
        # This would need context about what tool names exist in the codebase
        # The pattern-based check below handles common naming conventions
        self.generic_visit(node)


def check_tool_name_strings(source: str, file_path: str) -> list[LintError]:
    """
    Check for hardcoded tool name strings.

    This is a pattern-based check that looks for suspicious string literals
    that might be tool names. Customize the patterns based on your codebase.
    """
    errors: list[LintError] = []
    source_lines = source.splitlines()

    # Pattern for tool name strings (customize based on your conventions)
    # Example: looks for strings that match tool naming patterns
    tool_name_pattern = re.compile(r'["\']([a-z_]+_tool|tool_[a-z_]+)["\']', re.IGNORECASE)

    for i, line in enumerate(source_lines, 1):
        if is_suppressed(line, "tool-name-string") or is_in_allowlist(file_path, "tool-name-string"):
            continue

        matches = tool_name_pattern.findall(line)
        for match in matches:
            # Skip if it looks like it's using ToolClass.name
            if ".name" not in line:
                errors.append(
                    LintError(
                        file_path,
                        i,
                        "tool-name-string",
                        f"Hardcoded tool name string '{match}'. Use ToolClass.name instead.",
                    )
                )

    return errors


def lint_file(file_path: str) -> list[LintError]:
    """Lint a single Python file."""
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError) as e:
        return [LintError(file_path, 0, "error", f"Could not read file: {e}")]

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [LintError(file_path, e.lineno or 0, "error", f"Syntax error: {e.msg}")]

    visitor = LintVisitor(file_path, source)
    visitor.visit(tree)

    # Add tool name string checks
    errors = visitor.errors + check_tool_name_strings(source, file_path)

    return errors


def find_python_files(directory: str) -> list[str]:
    """Find all Python files in a directory, excluding migrations and venv."""
    excluded_patterns = [
        "**/migrations/**",
        "**/.venv/**",
        "**/venv/**",
        "**/__pycache__/**",
        "**/node_modules/**",
    ]

    files = []
    for path in Path(directory).rglob("*.py"):
        path_str = str(path)
        if not any(Path(path_str).match(pattern) for pattern in excluded_patterns):
            files.append(path_str)

    return sorted(files)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Custom lint rules for Plane backend")
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to check. If not specified, checks all Python files in plane/",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose output",
    )
    args = parser.parse_args()

    if args.files:
        files = args.files
    else:
        # Default to checking all Python files in the plane directory
        script_dir = Path(__file__).parent.parent
        plane_dir = script_dir / "plane"
        if plane_dir.exists():
            files = find_python_files(str(plane_dir))
        else:
            print("Error: plane/ directory not found", file=sys.stderr)
            return 1

    if args.verbose:
        print(f"Checking {len(files)} files...", file=sys.stderr)

    all_errors: list[LintError] = []
    for file_path in files:
        errors = lint_file(file_path)
        all_errors.extend(errors)

    if all_errors:
        for error in sorted(all_errors, key=lambda e: (e.file, e.line)):
            print(f"{error.file}:{error.line}: [{error.rule}] {error.message}")
        return 1

    if args.verbose:
        print("No lint errors found.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
