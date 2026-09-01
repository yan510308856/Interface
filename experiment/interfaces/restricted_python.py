"""Small AST-interpreted Python action adapter with narrow backend capabilities."""

from __future__ import annotations

import ast
import operator
import time
from typing import Any

from experiment import backend
from experiment.interfaces import ActionResult, format_observation


class RestrictedPythonError(ValueError):
    pass


PROXY_OPERATIONS = {
    "repo": {"list_dir", "search_text", "read_file", "replace_text", "create_file", "delete_file", "git_diff"},
    "runner": {"run_process"},
}
CONTROL_CALLS = {"finish"}


class _Validator(ast.NodeVisitor):
    _simple = (
        ast.Module, ast.Expr, ast.Assign, ast.If, ast.For, ast.Constant, ast.List,
        ast.Tuple, ast.Dict, ast.Name, ast.Load, ast.Store, ast.Subscript,
        ast.BoolOp, ast.And, ast.Or, ast.UnaryOp, ast.Not, ast.USub,
        ast.BinOp, ast.Add, ast.Compare, ast.Eq, ast.NotEq, ast.In, ast.NotIn,
        ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Call, ast.Attribute, ast.keyword,
    )

    def generic_visit(self, node: ast.AST) -> None:
        if not isinstance(node, self._simple):
            raise RestrictedPythonError(f"syntax is not allowed: {type(node).__name__}")
        super().generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id.startswith("_"):
            raise RestrictedPythonError("private names are not allowed")

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            raise RestrictedPythonError("assignment target must be one local name")
        self.visit(node.targets[0])
        self.visit(node.value)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        raise RestrictedPythonError("attribute access is allowed only for capability calls")

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in CONTROL_CALLS:
            if len(node.args) > 1 or node.keywords:
                raise RestrictedPythonError("finish accepts at most one positional message")
            for argument in node.args:
                self.visit(argument)
            return
        if not isinstance(node.func, ast.Attribute) or not isinstance(node.func.value, ast.Name):
            raise RestrictedPythonError("only repo/runner capability calls are allowed")
        proxy = node.func.value.id
        if proxy not in PROXY_OPERATIONS or node.func.attr not in PROXY_OPERATIONS[proxy]:
            raise RestrictedPythonError("capability method is not allowed")
        if any(keyword.arg is None for keyword in node.keywords):
            raise RestrictedPythonError("expanded keyword arguments are not allowed")
        for argument in node.args:
            self.visit(argument)
        for keyword in node.keywords:
            self.visit(keyword.value)

    def visit_For(self, node: ast.For) -> None:
        if node.orelse or not isinstance(node.target, ast.Name):
            raise RestrictedPythonError("for must bind one name and cannot use else")
        iterator = node.iter
        if not (
            isinstance(iterator, ast.Call)
            and isinstance(iterator.func, ast.Name)
            and iterator.func.id == "range"
            and not iterator.keywords
            and 1 <= len(iterator.args) <= 3
        ):
            raise RestrictedPythonError("for loops require range with one to three arguments")
        self.visit(node.target)
        for argument in iterator.args:
            self.visit(argument)
        for statement in node.body:
            self.visit(statement)


class _Interpreter:
    def __init__(self, context: backend.BackendContext, action_id: str) -> None:
        self.context = context
        self.action_id = action_id
        self.locals: dict[str, Any] = {}
        self.responses: list[dict[str, Any]] = []
        self.schema = backend.load_schema()
        self.loop_limit = context.permission.policy["resource_limits"]["restricted_python_loop_iterations"]
        self.loop_iterations = 0
        self.finished = False

    def run(self, tree: ast.Module) -> list[dict[str, Any]]:
        self._statements(tree.body)
        return self.responses

    def _statements(self, statements: list[ast.stmt]) -> None:
        for statement in statements:
            if self.finished:
                break
            if isinstance(statement, ast.Assign):
                self.locals[statement.targets[0].id] = self._expression(statement.value)
            elif isinstance(statement, ast.Expr):
                self._expression(statement.value)
            elif isinstance(statement, ast.If):
                branch = statement.body if self._expression(statement.test) else statement.orelse
                self._statements(branch)
            elif isinstance(statement, ast.For):
                values = self._range(statement.iter)
                self.loop_iterations += len(values)
                if self.loop_iterations > self.loop_limit:
                    raise RestrictedPythonError("loop iteration limit exceeded")
                for value in values:
                    self.locals[statement.target.id] = value
                    self._statements(statement.body)
            else:
                raise RestrictedPythonError(f"statement is not allowed: {type(statement).__name__}")

    def _range(self, call: ast.Call) -> range:
        values = [self._expression(argument) for argument in call.args]
        if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
            raise RestrictedPythonError("range arguments must be integers")
        try:
            result = range(*values)
        except ValueError as exc:
            raise RestrictedPythonError(str(exc)) from exc
        if len(result) > self.loop_limit:
            raise RestrictedPythonError("loop iteration limit exceeded")
        return result

    def _expression(self, node: ast.expr) -> Any:
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (str, int, bool, type(None))):
                raise RestrictedPythonError("literal type is not allowed")
            return node.value
        if isinstance(node, (ast.List, ast.Tuple)):
            values = [self._expression(item) for item in node.elts]
            return values if isinstance(node, ast.List) else tuple(values)
        if isinstance(node, ast.Dict):
            return {self._expression(key): self._expression(value) for key, value in zip(node.keys, node.values)}
        if isinstance(node, ast.Name):
            if node.id not in self.locals:
                raise RestrictedPythonError(f"unknown local name: {node.id}")
            return self.locals[node.id]
        if isinstance(node, ast.Subscript):
            value = self._expression(node.value)
            key = self._expression(node.slice)
            if not isinstance(value, (dict, list, tuple, str)):
                raise RestrictedPythonError("subscript target type is not allowed")
            return value[key]
        if isinstance(node, ast.BoolOp):
            if isinstance(node.op, ast.And):
                for item in node.values:
                    if not self._expression(item):
                        return False
                return True
            for item in node.values:
                if self._expression(item):
                    return True
            return False
        if isinstance(node, ast.UnaryOp):
            value = self._expression(node.operand)
            if isinstance(node.op, ast.Not):
                return not value
            if isinstance(node.op, ast.USub) and isinstance(value, int) and not isinstance(value, bool):
                return -value
            raise RestrictedPythonError("unary operation is not allowed")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left, right = self._expression(node.left), self._expression(node.right)
            if type(left) is type(right) and isinstance(left, (str, int, list, tuple)):
                return operator.add(left, right)
            raise RestrictedPythonError("addition operand types do not match")
        if isinstance(node, ast.Compare):
            return self._compare(node)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "finish":
                message = self._expression(node.args[0]) if node.args else ""
                if not isinstance(message, str):
                    raise RestrictedPythonError("finish message must be a string")
                self.finished = True
                return {"ok": True, "type": "finish", "message": message}
            return self._capability_call(node)
        raise RestrictedPythonError(f"expression is not allowed: {type(node).__name__}")

    def _compare(self, node: ast.Compare) -> bool:
        operations = {
            ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.In: operator.contains,
            ast.NotIn: lambda right, left: not operator.contains(right, left),
            ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
        }
        left = self._expression(node.left)
        for operation, comparator in zip(node.ops, node.comparators):
            right = self._expression(comparator)
            function = operations[type(operation)]
            if isinstance(operation, (ast.In, ast.NotIn)):
                matched = function(right, left)
            else:
                matched = function(left, right)
            if not matched:
                return False
            left = right
        return True

    def _capability_call(self, node: ast.Call) -> dict[str, Any]:
        operation = node.func.attr
        parameter_names = list(self.schema["operations"][operation]["parameters"])
        if len(node.args) > len(parameter_names):
            raise RestrictedPythonError("too many positional arguments")
        arguments = {
            name: self._expression(value)
            for name, value in zip(parameter_names, node.args)
        }
        for keyword in node.keywords:
            if keyword.arg in arguments:
                raise RestrictedPythonError(f"duplicate argument: {keyword.arg}")
            arguments[keyword.arg] = self._expression(keyword.value)
        request_id = f"{self.action_id}:op{len(self.responses) + 1}"
        response = backend.execute(
            {"operation": operation, "arguments": arguments, "request_id": request_id},
            self.context,
            self.schema,
        )
        self.responses.append(response)
        return response


def execute_action(source: str, context: backend.BackendContext, action_id: str) -> ActionResult:
    """Validate and interpret one restricted program without using eval or exec."""
    started = time.monotonic()
    responses: list[dict[str, Any]] = []
    interpreter: _Interpreter | None = None
    try:
        if not isinstance(source, str) or len(source) > 16384:
            raise RestrictedPythonError("program must be a string of at most 16384 characters")
        if "```" in source:
            raise RestrictedPythonError("program must be raw Python source without Markdown fences")
        tree = ast.parse(source, mode="exec")
        if len(list(ast.walk(tree))) > 500:
            raise RestrictedPythonError("program AST is too large")
        _Validator().visit(tree)
        context.action_id = action_id
        interpreter = _Interpreter(context, action_id)
        responses = interpreter.run(tree)
    except (SyntaxError, RestrictedPythonError, KeyError, IndexError, OverflowError, TypeError) as exc:
        if interpreter is not None:
            responses = interpreter.responses
        error = {"code": "invalid_action", "message": str(exc), "retryable": False}
        return ActionResult(
            action_id=action_id,
            parse_status="invalid",
            backend_op_ids=[response["request_id"] for response in responses],
            observation=format_observation(responses + [{"ok": False, "error": error}]),
            error=error,
            duration_ms=round((time.monotonic() - started) * 1000, 3),
            backend_responses=responses,
        )

    backend_error = next((response["error"] for response in responses if not response["ok"]), None)
    return ActionResult(
        action_id=action_id,
        parse_status="finish" if interpreter and interpreter.finished else "ok",
        backend_op_ids=[response["request_id"] for response in responses],
        observation=format_observation(responses),
        error=backend_error,
        duration_ms=round((time.monotonic() - started) * 1000, 3),
        backend_responses=responses,
    )
