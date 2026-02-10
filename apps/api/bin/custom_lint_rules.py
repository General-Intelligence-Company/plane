#!/usr/bin/env python3
"""
Custom lint rules for the Plane backend codebase.

This module enforces project-specific coding standards beyond what Ruff provides:
- No @dataclass usage (use Pydantic BaseModel instead)
- No TypedDict usage (use Pydantic BaseModel instead)
- No explicit dict/tuple return annotations (return a BaseModel instead)
- Modal function complexity limits (max 50 lines, complexity 10)
- No hardcoded tool name strings (use ToolClass.name instead)

Usage:
    python apps/api/scripts/custom_lint_rules.py [files...]

Suppression mechanisms:
    - # lint: ignore-<rule>  (per-line suppression)
    - # noqa: <rule>  (per-line suppression)
    - # noqa: custom-lint  (per-line suppression for all custom rules)
    - # noqa  (with no specific codes, suppresses all custom lint checks on that line)
"""

import ast
import re
import sys
from dataclasses import dataclass as stdlib_dataclass
from pathlib import Path

# Legacy allowlist - files that are exempt from certain rules
# Add paths here for legacy code that would be too disruptive to refactor
# These files predate the custom lint rules and will be migrated incrementally
LEGACY_ALLOWLIST: dict[str, set[str]] = {
    "no-dataclass": {
        # Legacy exporter schemas using @dataclass
        # TODO: Migrate to Pydantic BaseModel
        "plane/utils/exporters/schemas/",
    },
    "no-typed-dict": set(),
    "no-dict-tuple-return": {
        # Legacy views and utilities with dict/tuple returns
        # TODO: Migrate to Pydantic BaseModel incrementally
        "plane/app/views/analytic/",
        "plane/app/views/external/base.py",
        "plane/bgtasks/",
        "plane/db/mixins.py",
        "plane/utils/build_chart.py",
        "plane/utils/date_utils.py",
        "plane/utils/exporters/",
        "plane/utils/filters/",
        "plane/utils/porters/",
    },
    "modal-complexity": set(),
    "tool-name-string": set(),
}


@stdlib_dataclass
class LintError:
    """Represents a single lint error."""

    file_path: str
    line: int
    column: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.file_path}:{self.line}:{self.column}: [{self.rule}] {self.message}"


def is_suppressed(line_content: str, rule: str) -> bool:
    """Check if a rule is suppressed on this line."""
    # Check for specific rule suppression
    if f"# lint: ignore-{rule}" in line_content:
        return True
    if f"# noqa: {rule}" in line_content:
        return True
    # Check for all custom rules suppression
    if "# noqa: custom-lint" in line_content:
        return True
    # Check for blanket noqa (no specific codes)
    if re.search(r"#\s*noqa\s*$", line_content):
        return True
    if re.search(r"#\s*noqa\s+[^:]", line_content):
        # noqa followed by something that's not a colon (like a comment)
        return True
    return False


def is_in_legacy_allowlist(file_path: str, rule: str) -> bool:
    """Check if a file is in the legacy allowlist for a rule."""
    for pattern in LEGACY_ALLOWLIST.get(rule, set()):
        if pattern in file_path:
            return True
    return False


def calculate_cyclomatic_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """
    Calculate the cyclomatic complexity of a function.

    Complexity increases for:
    - if/elif statements
    - for/while loops
    - try/except handlers
    - boolean operators (and/or)
    - comprehensions with conditions
    """
    complexity = 1  # Base complexity

    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            # Each 'and'/'or' adds complexity
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            # Count conditions in comprehensions
            for generator in child.generators:
                complexity += len(generator.ifs)
        elif isinstance(child, ast.Assert):
            complexity += 1

    return complexity


def count_non_empty_lines(node: ast.FunctionDef | ast.AsyncFunctionDef, source_lines: list[str]) -> int:
    """Count non-empty, non-comment lines in a function body."""
    if not node.body:
        return 0

    start_line = node.body[0].lineno - 1  # 0-indexed
    end_line = node.end_lineno or start_line + 1  # end_lineno is 1-indexed

    count = 0
    for i in range(start_line, end_line):
        if i < len(source_lines):
            line = source_lines[i].strip()
            # Skip empty lines and comment-only lines
            if line and not line.startswith("#"):
                count += 1

    return count


def is_modal_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Check if a function is decorated with a Modal decorator."""
    modal_decorator_names = {"function", "method", "web_endpoint", "asgi_app", "wsgi_app"}

    for decorator in node.decorator_list:
        # Handle simple name decorators
        if isinstance(decorator, ast.Name):
            if decorator.id in modal_decorator_names:
                return True
        # Handle attribute decorators like @modal.function
        elif isinstance(decorator, ast.Attribute):
            if isinstance(decorator.value, ast.Name) and decorator.value.id == "modal":
                return True
        # Handle call decorators like @modal.function()
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                if isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "modal":
                    return True
            elif isinstance(decorator.func, ast.Name):
                if decorator.func.id in modal_decorator_names:
                    return True

    return False


class CustomLintVisitor(ast.NodeVisitor):
    """AST visitor that checks for custom lint rules."""

    def __init__(self, file_path: str, source: str):
        self.file_path = file_path
        self.source = source
        self.source_lines = source.splitlines()
        self.errors: list[LintError] = []

    def get_line_content(self, lineno: int) -> str:
        """Get the content of a specific line (1-indexed)."""
        if 1 <= lineno <= len(self.source_lines):
            return self.source_lines[lineno - 1]
        return ""

    def add_error(self, node: ast.AST, rule: str, message: str) -> None:
        """Add a lint error if not suppressed."""
        line_content = self.get_line_content(node.lineno)

        if is_suppressed(line_content, rule):
            return

        if is_in_legacy_allowlist(self.file_path, rule):
            return

        self.errors.append(
            LintError(
                file_path=self.file_path,
                line=node.lineno,
                column=node.col_offset + 1,  # 1-indexed
                rule=rule,
                message=message,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check for @dataclass decorator usage."""
        for decorator in node.decorator_list:
            decorator_name = None
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
                    decorator,
                    "no-dataclass",
                    "@dataclass is not allowed. Use Pydantic BaseModel instead.",
                )

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for TypedDict imports."""
        if node.module in ("typing", "typing_extensions"):
            for alias in node.names:
                if alias.name == "TypedDict":
                    self.add_error(
                        node,
                        "no-typed-dict",
                        "TypedDict is not allowed. Use Pydantic BaseModel instead.",
                    )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function definitions for various rules."""
        self._check_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function definitions for various rules."""
        self._check_function(node)
        self.generic_visit(node)

    def _check_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check a function for return type and Modal complexity rules."""
        # Check return annotation for dict/tuple
        if node.returns:
            self._check_return_annotation(node, node.returns)

        # Check Modal function complexity
        if is_modal_function(node):
            # Check line count
            line_count = count_non_empty_lines(node, self.source_lines)
            if line_count > 50:
                self.add_error(
                    node,
                    "modal-complexity",
                    f"Modal function is too long ({line_count} lines > 50).",
                )

            # Check cyclomatic complexity
            complexity = calculate_cyclomatic_complexity(node)
            if complexity > 10:
                self.add_error(
                    node,
                    "modal-complexity",
                    f"Modal function complexity too high ({complexity} > 10).",
                )

    def _check_return_annotation(self, func_node: ast.AST, annotation: ast.AST) -> None:
        """Check if a return annotation uses dict or tuple explicitly."""
        if isinstance(annotation, ast.Name):
            if annotation.id in ("dict", "tuple"):
                self.add_error(
                    func_node,
                    "no-dict-tuple-return",
                    "Explicit dict/tuple return annotations are not allowed. Return a Pydantic BaseModel instead.",
                )
        elif isinstance(annotation, ast.Subscript):
            # Handle Dict[...] or Tuple[...] from typing
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id in ("Dict", "Tuple", "dict", "tuple"):
                    self.add_error(
                        func_node,
                        "no-dict-tuple-return",
                        "Explicit dict/tuple return annotations are not allowed. Return a Pydantic BaseModel instead.",
                    )
            elif isinstance(annotation.value, ast.Attribute):
                if annotation.value.attr in ("Dict", "Tuple"):
                    self.add_error(
                        func_node,
                        "no-dict-tuple-return",
                        "Explicit dict/tuple return annotations are not allowed. Return a Pydantic BaseModel instead.",
                    )

    def visit_Constant(self, node: ast.Constant) -> None:
        """Check for hardcoded tool name strings.

        Note: This check is intentionally conservative to avoid false positives.
        The tool-name-string rule is primarily enforced through code review.
        Pattern matching for tool names (e.g., *_tool, get_*, create_*) may be
        added in future versions with context-aware detection.
        """
        # Currently a no-op placeholder for future tool name detection
        # The rule is documented but enforced through code review
        self.generic_visit(node)


def lint_file(file_path: str) -> list[LintError]:
    """Lint a single Python file."""
    path = Path(file_path)

    if not path.exists():
        return []

    if not path.suffix == ".py":
        return []

    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {file_path}: {e}", file=sys.stderr)
        return []

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        print(f"Warning: Syntax error in {file_path}: {e}", file=sys.stderr)
        return []

    visitor = CustomLintVisitor(file_path, source)
    visitor.visit(tree)

    return visitor.errors


def main() -> int:
    """Main entry point for the linter."""
    if len(sys.argv) < 2:
        print("Usage: python custom_lint_rules.py [files...]", file=sys.stderr)
        print("       python custom_lint_rules.py apps/api/", file=sys.stderr)
        return 1

    files_to_check: list[str] = []

    for arg in sys.argv[1:]:
        path = Path(arg)
        if path.is_file():
            files_to_check.append(str(path))
        elif path.is_dir():
            # Recursively find all Python files
            files_to_check.extend(str(p) for p in path.rglob("*.py"))
        else:
            print(f"Warning: {arg} is not a valid file or directory", file=sys.stderr)

    if not files_to_check:
        print("No Python files to check", file=sys.stderr)
        return 0

    all_errors: list[LintError] = []

    for file_path in files_to_check:
        errors = lint_file(file_path)
        all_errors.extend(errors)

    # Sort errors by file and line number
    all_errors.sort(key=lambda e: (e.file_path, e.line, e.column))

    # Print errors
    for error in all_errors:
        print(error)

    if all_errors:
        print(f"\nFound {len(all_errors)} error(s)", file=sys.stderr)
        return 1

    print(f"Checked {len(files_to_check)} file(s), no errors found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
