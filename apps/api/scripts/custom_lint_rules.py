#!/usr/bin/env python3
"""
Custom lint rules for the Plane backend codebase.

This script enforces project-specific conventions that aren't covered by standard
linters like Ruff. Run it on Python files to check for violations.

Usage:
    python custom_lint_rules.py [files...]
    python custom_lint_rules.py apps/api/plane/api/views.py
    python custom_lint_rules.py $(git diff --name-only --diff-filter=d HEAD~1 -- '*.py')

Suppression:
    # lint: ignore-<rule>     (per-line)
    # noqa: <rule>            (per-line)
    # noqa: custom-lint       (per-line, all custom rules)
    # noqa                    (per-line, all rules)

Rules:
    no-dataclass           - No @dataclass usage; use Pydantic BaseModel
    no-typed-dict          - No TypedDict usage; use Pydantic BaseModel
    no-dict-tuple-return   - No explicit dict/tuple return annotations
    modal-complexity       - Modal functions must be <= 50 lines, complexity <= 10
    tool-name-string       - No hardcoded tool name strings; use ToolClass.name
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

# Legacy allowlist for gradual migration
# These files contain existing violations that should be cleaned up over time.
# New code should NOT be added to this allowlist.
LEGACY_ALLOWLIST: dict[str, set[str]] = {
    "no-dataclass": {
        # Existing files using @dataclass - should migrate to Pydantic BaseModel
        "plane/utils/exporters/schemas/",
    },
    "no-typed-dict": {
        # Add paths that are allowed to use TypedDict during migration
    },
    "no-dict-tuple-return": {
        # Existing files with dict/tuple return annotations - clean up gradually
        "plane/app/views/analytic/",
        "plane/app/views/external/",
        "plane/bgtasks/",
        "plane/db/mixins.py",
        "plane/utils/build_chart.py",
        "plane/utils/date_utils.py",
        "plane/utils/exporters/",
        "plane/utils/filters/",
        "plane/utils/openapi/",
        "plane/utils/porters/",
    },
    "tool-name-string": {
        # Existing files with hardcoded tool name strings - clean up gradually
        "plane/authentication/urls.py",
        "plane/db/models/",
        "plane/utils/openapi/",
    },
}


@dataclass
class LintError:
    """Represents a lint error."""

    file: str
    line: int
    column: int
    rule: str
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}:{self.column}: [{self.rule}] {self.message}"


class CustomLinter(ast.NodeVisitor):
    """AST-based linter for custom rules."""

    def __init__(self, filename: str, source: str) -> None:
        self.filename = filename
        self.source = source
        self.lines = source.splitlines()
        self.errors: list[LintError] = []

    def _is_suppressed(self, lineno: int, rule: str) -> bool:
        """Check if a rule is suppressed on the given line."""
        if lineno < 1 or lineno > len(self.lines):
            return False

        line = self.lines[lineno - 1]

        # Check for various suppression patterns
        suppression_patterns = [
            rf"#\s*lint:\s*ignore-{rule}",  # lint: ignore-<rule>
            rf"#\s*noqa:\s*{rule}",  # noqa: <rule>
            r"#\s*noqa:\s*custom-lint",  # noqa: custom-lint (all custom rules)
            r"#\s*noqa\s*$",  # noqa (all rules)
        ]

        return any(re.search(pattern, line) for pattern in suppression_patterns)

    def _is_in_legacy_allowlist(self, rule: str) -> bool:
        """Check if the file is in the legacy allowlist for a rule."""
        if rule not in LEGACY_ALLOWLIST:
            return False
        return any(
            pattern in self.filename for pattern in LEGACY_ALLOWLIST[rule]
        )

    def _add_error(
        self, node: ast.AST, rule: str, message: str
    ) -> None:
        """Add an error if not suppressed."""
        lineno = getattr(node, "lineno", 1)
        col_offset = getattr(node, "col_offset", 0)

        if self._is_suppressed(lineno, rule):
            return
        if self._is_in_legacy_allowlist(rule):
            return

        self.errors.append(
            LintError(
                file=self.filename,
                line=lineno,
                column=col_offset + 1,
                rule=rule,
                message=message,
            )
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """Check for @dataclass decorator usage."""
        for decorator in node.decorator_list:
            decorator_name = None
            if isinstance(decorator, ast.Name):
                decorator_name = decorator.id
            elif isinstance(decorator, ast.Call) and isinstance(
                decorator.func, ast.Name
            ):
                decorator_name = decorator.func.id
            elif isinstance(decorator, ast.Attribute):
                decorator_name = decorator.attr

            if decorator_name == "dataclass":
                self._add_error(
                    decorator,
                    "no-dataclass",
                    "@dataclass is not allowed. Use Pydantic BaseModel instead.",
                )

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """Check for TypedDict imports."""
        if node.module in ("typing", "typing_extensions"):
            for alias in node.names:
                if alias.name == "TypedDict":
                    self._add_error(
                        node,
                        "no-typed-dict",
                        "TypedDict is not allowed. Use Pydantic BaseModel instead.",
                    )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Check function return annotations and complexity."""
        self._check_return_annotation(node)
        self._check_modal_complexity(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """Check async function return annotations and complexity."""
        self._check_return_annotation(node)
        self._check_modal_complexity(node)
        self.generic_visit(node)

    def _check_return_annotation(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Check for dict/tuple return type annotations."""
        if node.returns is None:
            return

        annotation = node.returns

        # Check for dict or tuple at the top level
        if isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                if annotation.value.id in ("dict", "Dict", "tuple", "Tuple"):
                    self._add_error(
                        annotation,
                        "no-dict-tuple-return",
                        "Explicit dict/tuple return annotations are not allowed. "
                        "Return a Pydantic BaseModel instead.",
                    )
        elif isinstance(annotation, ast.Name):
            if annotation.id in ("dict", "Dict", "tuple", "Tuple"):
                self._add_error(
                    annotation,
                    "no-dict-tuple-return",
                    "Explicit dict/tuple return annotations are not allowed. "
                    "Return a Pydantic BaseModel instead.",
                )

    def _check_modal_complexity(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Check Modal function complexity (line count and cyclomatic complexity)."""
        # Check if this is a Modal function (decorated with @modal.* or @app.*)
        is_modal = False
        for decorator in node.decorator_list:
            decorator_str = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
            if any(
                pattern in decorator_str
                for pattern in ["modal.", "app.function", "app.local_entrypoint"]
            ):
                is_modal = True
                break

        if not is_modal:
            return

        # Count non-empty, non-comment lines
        if node.end_lineno is None:
            return

        line_count = 0
        for i in range(node.lineno, node.end_lineno + 1):
            if i <= len(self.lines):
                line = self.lines[i - 1].strip()
                if line and not line.startswith("#"):
                    line_count += 1

        if line_count > 50:
            self._add_error(
                node,
                "modal-complexity",
                f"Modal function is too long ({line_count} lines > 50).",
            )

        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)
        if complexity > 10:
            self._add_error(
                node,
                "modal-complexity",
                f"Modal function complexity too high ({complexity} > 10).",
            )

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a node."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Each decision point adds 1 to complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.Assert):
                complexity += 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # and/or operators add branches
                complexity += len(child.values) - 1
            elif isinstance(child, ast.IfExp):  # Ternary operator
                complexity += 1
            elif isinstance(child, ast.Match):  # match statement (Python 3.10+)
                complexity += len(child.cases) - 1

        return complexity

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """Check for hardcoded tool name strings."""
        # Look for patterns like tool_name="some_tool" or name="some_tool" in calls
        for keyword in node.keywords:
            if keyword.arg in ("tool_name", "name") and isinstance(
                keyword.value, ast.Constant
            ):
                if isinstance(keyword.value.value, str):
                    # Check if it looks like a tool name (snake_case identifier)
                    value = keyword.value.value
                    if re.match(r"^[a-z][a-z0-9_]*$", value) and "_" in value:
                        self._add_error(
                            keyword.value,
                            "tool-name-string",
                            "Hardcoded tool name string. Use ToolClass.name instead.",
                        )

        self.generic_visit(node)


def lint_file(filepath: Path) -> list[LintError]:
    """Lint a single file and return errors."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [
            LintError(
                file=str(filepath),
                line=1,
                column=1,
                rule="file-error",
                message=f"Could not read file: {e}",
            )
        ]

    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as e:
        return [
            LintError(
                file=str(filepath),
                line=e.lineno or 1,
                column=e.offset or 1,
                rule="syntax-error",
                message=f"Syntax error: {e.msg}",
            )
        ]

    linter = CustomLinter(str(filepath), source)
    linter.visit(tree)
    return linter.errors


def find_python_files(paths: list[str]) -> Iterator[Path]:
    """Find all Python files in the given paths."""
    for path_str in paths:
        path = Path(path_str)
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            yield from path.rglob("*.py")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Custom lint rules for the Plane backend codebase."
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=["."],
        help="Files or directories to lint (default: current directory)",
    )
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Only output errors, no summary",
    )

    args = parser.parse_args()

    all_errors: list[LintError] = []
    file_count = 0

    for filepath in find_python_files(args.files):
        # Skip migrations and other generated files
        if "migrations" in filepath.parts:
            continue
        if filepath.name.startswith("_"):
            continue

        file_count += 1
        errors = lint_file(filepath)
        all_errors.extend(errors)

    # Output errors
    for error in all_errors:
        print(error)

    # Summary
    if not args.quiet:
        if all_errors:
            print(f"\nFound {len(all_errors)} error(s) in {file_count} file(s)")
        else:
            print(f"\nNo errors found in {file_count} file(s)")

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
