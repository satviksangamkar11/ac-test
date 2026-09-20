"""Test that transcript evidence layer maintains Claude/API boundary.

Verifies: serum2/evidence contains no Anthropic SDK or API usage.
This is a structural guarantee that Claude Code cannot become a reasoning layer.
"""

import ast
import os
from pathlib import Path


class ImportVisitor(ast.NodeVisitor):
    """Collect all imports from an AST."""

    def __init__(self):
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module)
        self.generic_visit(node)


def test_evidence_layer_no_anthropic_sdk():
    """No anthropic SDK imports in serum2/evidence/."""
    evidence_dir = Path(__file__).parent

    forbidden_patterns = {
        "anthropic",
        "anthropic.sdk",
        "anthropic.messages",
        "anthropic.beta",
        "anthropic_sdk",
    }

    for py_file in evidence_dir.glob("*.py"):
        if py_file.name.startswith("test_"):
            continue  # Skip test files

        with open(py_file) as f:
            tree = ast.parse(f.read(), filename=py_file.name)

        visitor = ImportVisitor()
        visitor.visit(tree)

        forbidden_found = forbidden_patterns & visitor.imports
        assert (
            not forbidden_found
        ), f"{py_file.name} imports forbidden: {forbidden_found}"


def test_evidence_layer_no_api_keys():
    """No hardcoded API keys or credential patterns in serum2/evidence/."""
    evidence_dir = Path(__file__).parent

    dangerous_patterns = [
        "sk-",
        "ANTHROPIC_API_KEY",
        "api_key=",
        "token=",
    ]

    for py_file in evidence_dir.glob("*.py"):
        if py_file.name.startswith("test_"):
            continue

        with open(py_file) as f:
            content = f.read()

        for pattern in dangerous_patterns:
            assert (
                pattern not in content
            ), f"{py_file.name} contains credential pattern: {pattern}"
