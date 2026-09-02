"""AST-interpreted Python with access only to shared backend capabilities."""

from __future__ import annotations

import ast
import operator
from typing import Any

from experiment.backend import ARGUMENT_ORDER, Backend, OPERATIONS
from experiment.interfaces import ActionResult, observation


CAPABILITIES = {"repo": OPERATIONS - {"run_process"}, "runner": {"run_process"}}


class RestrictedPythonError(ValueError):
    def __init__(self, message: str, *, unsafe_attempt: bool = False) -> None:
        super().__init__(message)
        self.unsafe_attempt = unsafe_attempt


class Validator(ast.NodeVisitor):
    allowed = (
        ast.Module, ast.Expr, ast.Assign, ast.If, ast.For, ast.Constant, ast.List,
        ast.Tuple, ast.Dict, ast.Name, ast.Load, ast.Store, ast.Subscript,
        ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub,
        ast.BinOp, ast.Add, ast.Compare, ast.Eq, ast.NotEq, ast.In, ast.NotIn,
        ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Call, ast.Attribute, ast.keyword,
    )

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, self.allowed):
            raise RestrictedPythonError(
                f"syntax is not allowed: {type(node).__name__}",
                unsafe_attempt=isinstance(node, (ast.Import, ast.ImportFrom)),
            )
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("_"):
            raise RestrictedPythonError("private names are not allowed", unsafe_attempt=True)

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise RestrictedPythonError("assignment target must be one local name")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        raise RestrictedPythonError("attribute access is allowed only in capability calls")

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "finish":
            if len(node.args) > 1 or node.keywords:
                raise RestrictedPythonError("finish accepts at most one message")
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.attr not in CAPABILITIES.get(node.func.value.id, set()):
                raise RestrictedPythonError("capability method is not allowed", unsafe_attempt=True)
        else:
            raise RestrictedPythonError("only capability calls and finish are allowed", unsafe_attempt=True)
        for value in node.args:
            self.visit(value)
        for keyword in node.keywords:
            if keyword.arg is None:
                raise RestrictedPythonError("expanded keyword arguments are not allowed")
            self.visit(keyword.value)

    def visit_For(self, node: ast.For) -> None:
        if node.orelse or not isinstance(node.target, ast.Name):
            raise RestrictedPythonError("for must bind one name and cannot use else")
        if not (
            isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name)
            and node.iter.func.id == "range" and not node.iter.keywords
            and 1 <= len(node.iter.args) <= 3
        ):
            raise RestrictedPythonError("for loops require range")
        self.visit(node.target)
        for value in node.iter.args:
            self.visit(value)
        for statement in node.body:
            self.visit(statement)


class Interpreter:
    def __init__(self, backend: Backend, action_id: str, loop_limit: int = 1000) -> None:
        self.backend = backend
        self.action_id = action_id
        self.loop_limit = loop_limit
        self.locals: dict[str, Any] = {}
        self.responses: list[dict[str, Any]] = []
        self.finished = False
        self.loop_iterations = 0

    def run(self, tree: ast.Module) -> None:
        self.statements(tree.body)

    def statements(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            if self.finished:
                return
            if isinstance(statement, ast.Assign):
                self.locals[statement.targets[0].id] = self.expression(statement.value)
            elif isinstance(statement, ast.Expr):
                self.expression(statement.value)
            elif isinstance(statement, ast.If):
                self.statements(statement.body if self.expression(statement.test) else statement.orelse)
            elif isinstance(statement, ast.For):
                values = self.range_values(statement.iter)
                for value in values:
                    self.locals[statement.target.id] = value
                    self.statements(statement.body)
            else:
                raise RestrictedPythonError(f"statement is not allowed: {type(statement).__name__}")

    def range_values(self, call: ast.Call) -> range:
        values = [self.expression(value) for value in call.args]
        if any(type(value) is not int for value in values):
            raise RestrictedPythonError("range arguments must be integers")
        result = range(*values)
        self.loop_iterations += len(result)
        if self.loop_iterations > self.loop_limit:
            raise RestrictedPythonError("loop iteration limit exceeded")
        return result

    def expression(self, node: ast.expr) -> Any:
        if isinstance(node, ast.Constant) and isinstance(node.value, (str, int, bool, type(None))):
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [self.expression(value) for value in node.elts]
            return values if isinstance(node, ast.List) else tuple(values)
        if isinstance(node, ast.Dict):
            return {self.expression(key): self.expression(value) for key, value in zip(node.keys, node.values)}
        if isinstance(node, ast.Name):
            if node.id not in self.locals:
                raise RestrictedPythonError(f"unknown local name: {node.id}")
            return self.locals[node.id]
        if isinstance(node, ast.Subscript):
            return self.expression(node.value)[self.expression(node.slice)]
        if isinstance(node, ast.BoolOp):
            values = [bool(self.expression(value)) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.UnaryOp):
            value = self.expression(node.operand)
            if isinstance(node.op, ast.Not):
                return not value
            if isinstance(node.op, ast.USub) and type(value) is int:
                return -value
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return operator.add(self.expression(node.left), self.expression(node.right))
        if isinstance(node, ast.Compare):
            return self.compare(node)
        if isinstance(node, ast.Call):
            return self.call(node)
        raise RestrictedPythonError(f"expression is not allowed: {type(node).__name__}")

    def compare(self, node: ast.Compare) -> bool:
        functions = {
            ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
            ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
            ast.In: lambda left, right: left in right,
            ast.NotIn: lambda left, right: left not in right,
        }
        left = self.expression(node.left)
        for operation, comparator in zip(node.ops, node.comparators):
            right = self.expression(comparator)
            if not functions[type(operation)](left, right):
                return False
            left = right
        return True

    def call(self, node: ast.Call) -> Any:
        if isinstance(node.func, ast.Name):
            self.finished = True
            return None
        operation = node.func.attr
        names = ARGUMENT_ORDER[operation]
        if len(node.args) > len(names):
            raise RestrictedPythonError("too many positional arguments")
        arguments = {name: self.expression(value) for name, value in zip(names, node.args)}
        for keyword in node.keywords:
            if keyword.arg in arguments:
                raise RestrictedPythonError(f"duplicate argument: {keyword.arg}")
            arguments[keyword.arg] = self.expression(keyword.value)
        response = self.backend.execute(operation, arguments, self.action_id)
        self.responses.append(response)
        return response


def execute_action(source: str, backend: Backend, action_id: str) -> ActionResult:
    interpreter = Interpreter(backend, action_id)
    try:
        if not isinstance(source, str) or len(source) > 16384:
            raise RestrictedPythonError("program is too large")
        tree = ast.parse(source, mode="exec")
        if len(list(ast.walk(tree))) > 500:
            raise RestrictedPythonError("program AST is too large")
        Validator().visit(tree)
        interpreter.run(tree)
        status = "finish" if interpreter.finished else "ok"
        return ActionResult(status, observation(interpreter.responses), interpreter.responses)
    except (SyntaxError, KeyError, IndexError, TypeError, ValueError) as exc:
        return ActionResult(
            "invalid",
            observation(interpreter.responses + [{"error": str(exc)}]),
            interpreter.responses,
            getattr(exc, "unsafe_attempt", False),
        )
