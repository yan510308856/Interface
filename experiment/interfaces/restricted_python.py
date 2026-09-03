"""AST-interpreted Python with access only to shared backend capabilities."""

from __future__ import annotations

import ast
import operator
import re
from typing import Any

from experiment.backend import ARGUMENT_ORDER, Backend, OPERATIONS
from experiment.interfaces import ActionResult, observation


CAPABILITIES = {"repo": OPERATIONS - {"run_process"}, "runner": {"run_process"}}
KNOWN_CAPABILITY_NAMES = set().union(*CAPABILITIES.values())
UNSAFE_FUNCTION_NAMES = {"open", "exec", "eval", "compile", "__import__"}
UNSAFE_MODULE_NAMES = {"os", "subprocess", "socket", "pathlib", "shutil", "tempfile", "urllib", "http"}


class RestrictedPythonError(ValueError):
    def __init__(self, message: str, *, unsafe_attempt: bool = False) -> None:
        super().__init__(message)
        self.unsafe_attempt = unsafe_attempt


def _attribute_root_name(node: ast.AST) -> str | None:
    while isinstance(node, ast.Attribute):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _has_private_access(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id.startswith("_")
    if isinstance(node, ast.Attribute):
        return node.attr.startswith("_") or _has_private_access(node.value)
    return False


_FENCE_PATTERN = r"^[ \t]*```([^\n`]*)\n(.*?)^[ \t]*```[ \t]*(?=\n|$)"
_FENCE_MARKER_PATTERN = r"^[ \t]*```"


def _python_fences(source: str) -> list[re.Match[str]]:
    fences = list(re.finditer(_FENCE_PATTERN, source, re.MULTILINE | re.DOTALL))
    markers = list(re.finditer(_FENCE_MARKER_PATTERN, source, re.MULTILINE))
    if not fences:
        if markers:
            raise RestrictedPythonError("malformed or unclosed code fence")
        return []
    if len(markers) != len(fences) * 2:
        raise RestrictedPythonError("malformed or unclosed code fence")
    for fence in fences:
        language = fence.group(1).strip().lower()
        if language not in {"python", "py"}:
            raise RestrictedPythonError("code fence must contain Python")
    return fences


def _extract_program(source: str) -> str:
    fences = _python_fences(source)
    if not fences:
        return source
    return "\n".join(fence.group(2) for fence in fences)


def _strip_fenced_code(source: str) -> str:
    fences = _python_fences(source)
    if not fences:
        return source
    outside: list[str] = []
    end = 0
    for fence in fences:
        outside.append(source[end:fence.start()])
        end = fence.end()
    outside.append(source[end:])
    return "".join(outside)


_STANDALONE_FINISH = re.compile(
    r"^[ \t]*finish[ \t]*\([ \t]*(['\"])done\1[ \t]*\)[ \t]*\r?$",
    re.MULTILINE,
)
_STANDALONE_FINISH_CALL = re.compile(
    r"^[ \t]*finish[ \t]*\(.*\)[ \t]*\r?$",
    re.MULTILINE,
)
_EXECUTABLE_MARKERS = re.compile(
    r"(?mx)"
    r"^\s*(?:import|from|if|for|while|with|def|class|return|raise|assert|yield|try|except|finally|"
    r"async|await|del|pass|break|continue)\b"
    r"|^\s*[A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*\s*\("
    r"|^\s*[A-Za-z_]\w*\s*=",
)


def _is_prose_expression(line: str) -> bool:
    try:
        tree = ast.parse(line, mode="exec")
    except SyntaxError:
        return False
    return (
        len(tree.body) == 1
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Name)
    )


def _normalize_standalone_finish(program: str) -> str | None:
    """Extract a lone literal finish from otherwise non-Python prose."""
    matches = list(_STANDALONE_FINISH.finditer(program))
    if len(matches) != 1:
        return None

    match = matches[0]
    remainder = program[:match.start()] + program[match.end():]
    if not remainder.strip():
        return 'finish("done")'

    for line in remainder.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            ast.parse(stripped, mode="exec")
        except SyntaxError:
            if _EXECUTABLE_MARKERS.search(stripped):
                return None
        else:
            if not _is_prose_expression(stripped):
                return None
    return 'finish("done")'


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
        raise RestrictedPythonError(
            "attribute access is allowed only in capability calls",
            unsafe_attempt=_has_private_access(node) or _attribute_root_name(node) in UNSAFE_MODULE_NAMES,
        )

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "finish":
            if len(node.args) > 1 or node.keywords:
                raise RestrictedPythonError("finish accepts at most one message")
            if node.args and not (
                isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                raise RestrictedPythonError("finish message must be a literal")
        elif isinstance(node.func, ast.Name) and node.func.id in KNOWN_CAPABILITY_NAMES:
            raise RestrictedPythonError("capability calls must use their namespace")
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            namespace = node.func.value.id
            if node.func.attr in CAPABILITIES.get(namespace, set()):
                pass
            else:
                unsafe = (
                    namespace in CAPABILITIES
                    or namespace in UNSAFE_MODULE_NAMES
                    or namespace.startswith("_")
                    or node.func.attr.startswith("_")
                )
                raise RestrictedPythonError("capability method is not allowed", unsafe_attempt=unsafe)
        elif isinstance(node.func, ast.Attribute):
            raise RestrictedPythonError(
                "only capability calls and finish are allowed",
                unsafe_attempt=(
                    _attribute_root_name(node.func) in CAPABILITIES
                    or _attribute_root_name(node.func) in UNSAFE_MODULE_NAMES
                    or _has_private_access(node.func)
                ),
            )
        elif isinstance(node.func, ast.Name) and (
            node.func.id in UNSAFE_FUNCTION_NAMES or node.func.id.startswith("_")
        ):
            raise RestrictedPythonError("only capability calls and finish are allowed", unsafe_attempt=True)
        else:
            raise RestrictedPythonError("only capability calls and finish are allowed")
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
        outside_fences = _strip_fenced_code(source)
        if _STANDALONE_FINISH_CALL.search(outside_fences):
            normalized = _normalize_standalone_finish(outside_fences)
            program = normalized if normalized is not None else outside_fences
        else:
            program = _extract_program(source)
        tree = ast.parse(program, mode="exec")
        finish_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "finish"
        ]
        if len(list(ast.walk(tree))) > 500:
            raise RestrictedPythonError("program AST is too large")
        Validator().visit(tree)
        if len(finish_calls) > 1:
            raise RestrictedPythonError("only one finish call is allowed")
        if finish_calls:
            only_statement = (
                len(tree.body) == 1
                and isinstance(tree.body[0], ast.Expr)
                and tree.body[0].value is finish_calls[0]
            )
            if not only_statement:
                raise RestrictedPythonError("finish must be the only action")
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
