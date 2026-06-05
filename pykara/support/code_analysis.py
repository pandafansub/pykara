"""Static analysis helpers for Python code declarations."""

from __future__ import annotations

import ast


class _AssignedNameCollector(ast.NodeVisitor):
    """Collect module-scope names bound by a code declaration."""

    def __init__(self) -> None:
        self.names: set[str] = set()
        self.name_kinds: dict[str, str] = {}

    def _add_name(self, name: str, kind: str) -> None:
        self.names.add(name)
        self.name_kinds[name] = kind

    def _visit_function_definition(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        self._add_name(node.name, "function")
        for decorator in node.decorator_list:
            self.visit(decorator)
        if node.returns is not None:
            self.visit(node.returns)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._add_name(node.name, "class")
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._add_name(node.id, "variable")

    def visit_alias(self, node: ast.alias) -> None:
        self._add_name(node.asname or node.name.split(".", 1)[0], "variable")

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self._add_name(node.name, "variable")
        if node.type is not None:
            self.visit(node.type)
        for statement in node.body:
            self.visit(statement)

    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp,
    ) -> None:
        self.visit(node.elt)
        for generator in node.generators:
            self.visit(generator.iter)
            for condition in generator.ifs:
                self.visit(condition)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self.visit(node.key)
        self.visit(node.value)
        for generator in node.generators:
            self.visit(generator.iter)
            for condition in generator.ifs:
                self.visit(condition)


class _LoadedNameCollector(ast.NodeVisitor):
    """Collect Python names read by code or inline expressions."""

    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            self.names.add(node.id)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if isinstance(node.target, ast.Name):
            self.names.add(node.target.id)
        else:
            self.visit(node.target)
        self.visit(node.value)


def collect_assigned_names(tree: ast.AST) -> frozenset[str]:
    """Return user namespace names assigned by a code declaration tree."""

    collector = _AssignedNameCollector()
    collector.visit(tree)
    return frozenset(collector.names)


def collect_assigned_name_kinds(tree: ast.AST) -> dict[str, str]:
    """Return assigned user namespace names and their declaration kinds."""

    collector = _AssignedNameCollector()
    collector.visit(tree)
    return dict(collector.name_kinds)


def collect_loaded_names(tree: ast.AST) -> frozenset[str]:
    """Return Python names loaded by a code or expression tree."""

    collector = _LoadedNameCollector()
    collector.visit(tree)
    return frozenset(collector.names)
