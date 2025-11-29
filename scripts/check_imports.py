#!/usr/bin/env python3
"""Check for forbidden imports in the codebase.

This script enforces architectural boundaries by checking that:
1. CLI commands don't import directly from infrastructure (except designated adapters)
2. App layer doesn't import from infrastructure
3. Domain layer doesn't import from infrastructure

Usage:
    python scripts/check_imports.py
    python scripts/check_imports.py --verbose
    python scripts/check_imports.py --fix-suggestions
"""

from __future__ import annotations

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


@dataclass
class ImportViolation:
    """Represents a forbidden import."""

    file_path: Path
    line_number: int
    import_statement: str
    forbidden_module: str
    reason: str


@dataclass
class ImportRule:
    """Defines forbidden imports for a directory."""

    directory: str
    forbidden_patterns: List[str]
    exceptions: List[str] = field(default_factory=list)
    reason: str = ""


# Define architectural rules
IMPORT_RULES: List[ImportRule] = [
    ImportRule(
        directory="troostwatch/interfaces/cli",
        forbidden_patterns=[
            "troostwatch.infrastructure.db",
            "troostwatch.infrastructure.http",
        ],
        exceptions=[
            # Allowed adapter files
            "troostwatch/interfaces/cli/context.py",
            "troostwatch/interfaces/cli/context_helpers.py",
            "troostwatch/interfaces/cli/auth.py",
            "troostwatch/interfaces/cli/debug.py",  # Diagnostics are allowed
            # Only imports AuthenticationError exception
            "troostwatch/interfaces/cli/bid.py",
        ],
        reason="CLI commands should use services, not infrastructure directly",
    ),
    ImportRule(
        directory="troostwatch/app",
        forbidden_patterns=[
            "troostwatch.infrastructure.db.repositories",
            "troostwatch.infrastructure.db",
            "troostwatch.infrastructure.http",
        ],
        exceptions=[
            # Only dependencies.py is allowed to import infrastructure
            # It re-exports types for use in route type hints
            "troostwatch/app/dependencies.py",
        ],
        reason="App layer should use services, not infrastructure directly",
    ),
    ImportRule(
        directory="troostwatch/domain",
        forbidden_patterns=[
            "troostwatch.infrastructure",
        ],
        exceptions=[],
        reason="Domain layer must be independent of infrastructure",
    ),
]


# Sync layer boundary rules: enforce imports from troostwatch.services.sync only
SYNC_FORBIDDEN_PATTERNS = [
    "troostwatch.sync",  # Legacy sync location (should not exist)
    "troostwatch.services.sync.sync",  # Direct submodule import
    "troostwatch.services.sync.fetcher",  # Direct submodule import
    "troostwatch.services.sync.service",  # Direct submodule import
]

SYNC_EXCEPTIONS = [
    # The services/sync package itself can import from submodules
    "troostwatch/services/sync/__init__.py",
    "troostwatch/services/sync/sync.py",
    "troostwatch/services/sync/fetcher.py",
    "troostwatch/services/sync/service.py",
    # Test files that need to patch internal sync functions
    "tests/test_sync_failures.py",
    "tests/test_sync_logging.py",
    "tests/test_sync_pagination.py",
]


def check_sync_imports(base_path: Path) -> List[ImportViolation]:
    """Check that sync imports go through troostwatch.services.sync, not submodules."""
    violations = []

    # Check all Python files in troostwatch/ and tests/
    for search_dir in ["troostwatch", "tests"]:
        dir_path = base_path / search_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            rel_path = str(py_file.relative_to(base_path))

            # Skip exception files
            if any(exc in rel_path for exc in SYNC_EXCEPTIONS):
                continue

            for line_no, module in extract_imports(py_file):
                for forbidden in SYNC_FORBIDDEN_PATTERNS:
                    if module == forbidden or module.startswith(forbidden + "."):
                        violations.append(
                            ImportViolation(
                                file_path=py_file,
                                line_number=line_no,
                                import_statement=module,
                                forbidden_module=forbidden,
                                reason="Import sync from troostwatch.services.sync, not submodules",
                            )
                        )

    return violations


def extract_imports(file_path: Path) -> List[tuple[int, str]]:
    """
    Extract all import statements from a Python file.

    Args:
        file_path (Path): Path to the Python file.

    Returns:
        List[tuple[int, str]]: List of (line number, module name) tuples.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append((node.lineno, node.module))
    return imports


def check_file(file_path: Path, rule: ImportRule) -> List[ImportViolation]:
    """
    Check a single file against an import rule.

    Args:
        file_path (Path): Path to the Python file.
        rule (ImportRule): Import rule to check against.

    Returns:
        List[ImportViolation]: List of violations found in the file.
    """
    violations = []

    # Skip exception files
    rel_path = str(file_path)
    if any(exc in rel_path for exc in rule.exceptions):
        return violations

    for line_no, module in extract_imports(file_path):
        for forbidden in rule.forbidden_patterns:
            if module.startswith(forbidden) or f".{forbidden}" in module:
                violations.append(
                    ImportViolation(
                        file_path=file_path,
                        line_number=line_no,
                        import_statement=module,
                        forbidden_module=forbidden,
                        reason=rule.reason,
                    )
                )
    return violations


def check_directory(base_path: Path, rule: ImportRule) -> List[ImportViolation]:
    """
    Check all Python files in a directory against an import rule.

    Args:
        base_path (Path): Base path of the project.
        rule (ImportRule): Import rule to check against.

    Returns:
        List[ImportViolation]: List of violations found in the directory.
    """
    violations = []
    dir_path = base_path / rule.directory

    if not dir_path.exists():
        return violations

    for py_file in dir_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        violations.extend(check_file(py_file, rule))

    return violations


def main():
        """
        Main entry point for checking forbidden imports in the codebase.

        Usage:
            python scripts/check_imports.py [--verbose] [--fix-suggestions]
        """
    parser = argparse.ArgumentParser(description="Check for forbidden imports")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show all files checked"
    )
    parser.add_argument(
        "--fix-suggestions", action="store_true", help="Show fix suggestions"
    )
    args = parser.parse_args()

    base_path = Path(__file__).parent.parent
    all_violations: List[ImportViolation] = []

    for rule in IMPORT_RULES:
        violations = check_directory(base_path, rule)
        all_violations.extend(violations)

    # Check sync layer boundaries
    sync_violations = check_sync_imports(base_path)
    all_violations.extend(sync_violations)

    if not all_violations:
        print("✅ No import violations found!")
        return 0

    print(f"❌ Found {len(all_violations)} import violation(s):\n")

    for v in all_violations:
        print(f"  {v.file_path}:{v.line_number}")
        print(f"    Import: {v.import_statement}")
        print(f"    Reason: {v.reason}")
        if args.fix_suggestions:
            print("    Suggestion: Use a service or move to an adapter file")
        print()

    return 1


if __name__ == "__main__":
    sys.exit(main())
