"""A straight-line batch interface for the shared Backend.

Restricted Python is intentionally not a general Python interpreter. It only
validates and executes pre-composed canonical Backend calls, in source order.
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

from experiment.backend import ARGUMENT_ORDER, Backend, OPERATIONS
from experiment.interfaces import ActionResult


CAPABILITIES = {"repo": OPERATIONS - {"run_process"}, "runner": {"run_process"}}
RESTRICTED_PYTHON_TOOL_NAME = "execute_restricted_python"
RESTRICTED_PYTHON_TOOLS = [{
    "type": "function",
    "function": {
        "name": RESTRICTED_PYTHON_TOOL_NAME,
        "description": "Execute one straight-line batch of canonical Backend operations.",
        "parameters": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
            "additionalProperties": False,
        },
    },
}]
UNSAFE_FUNCTION_NAMES = {
    "open", "exec", "eval", "compile", "__import__", "Path", "globals", "locals", "vars",
    "getattr", "setattr", "delattr", "hasattr", "type", "object",
}
UNSAFE_MODULE_NAMES = {
    "os", "subprocess", "socket", "pathlib", "shutil", "tempfile", "urllib", "http",
    "requests", "glob", "sys", "inspect", "git",
}
LOCAL_COMPUTATION_METHODS = {
    "find", "startswith", "endswith", "strip", "split", "replace", "join", "append", "insert",
}
VALIDATION_ERROR_TYPE = "restricted_python_validation_error"
ENVELOPE_ERROR_TYPE = "restricted_python_envelope_error"


class RestrictedPythonError(ValueError):
    def __init__(self, message: str, *, unsafe_attempt: bool = False) -> None:
        super().__init__(message)
        self.unsafe_attempt = unsafe_attempt


def _error_observation(error_type: str, reason: str, backend_operations_executed: int) -> str:
    return json.dumps({
        "status": "invalid",
        "error_type": error_type,
        "reason": reason,
        "backend_operations_executed": backend_operations_executed,
    }, sort_keys=True)


def _batch_observation(responses: list[dict[str, Any]]) -> str:
    return json.dumps({"status": "ok", "operations": responses}, ensure_ascii=False, sort_keys=True)


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
        if fence.group(1).strip().lower() not in {"python", "py"}:
            raise RestrictedPythonError("code fence must contain Python")
    return fences


def _extract_program(source: str) -> str:
    fences = _python_fences(source)
    if not fences:
        return source
    if len(fences) != 1:
        raise RestrictedPythonError("expected at most one Python code fence")
    return fences[0].group(2)


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


_STANDALONE_FINISH_CALL = re.compile(r"^[ \t]*finish[ \t]*\(.*\)[ \t]*\r?$", re.MULTILINE)


class Validator(ast.NodeVisitor):
    """Validate the batch grammar without executing any operation."""

    def generic_visit(self, node: ast.AST) -> None:
        raise RestrictedPythonError(f"syntax is not allowed: {type(node).__name__}")

    def visit_Module(self, node: ast.Module) -> None:
        for statement in node.body:
            self.visit(statement)

    def visit_Expr(self, node: ast.Expr) -> None:
        if not isinstance(node.value, ast.Call):
            raise RestrictedPythonError("only canonical Backend capability calls are allowed")
        self.visit(node.value)

    def visit_Assign(self, node: ast.Assign) -> None:
        raise RestrictedPythonError("local assignment is not allowed in batch mode")

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        raise RestrictedPythonError("local assignment is not allowed in batch mode")

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        raise RestrictedPythonError("local assignment is not allowed in batch mode")

    def visit_If(self, node: ast.If) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_For(self, node: ast.For) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_While(self, node: ast.While) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_Break(self, node: ast.Break) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_Continue(self, node: ast.Continue) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_Try(self, node: ast.Try) -> None:
        raise RestrictedPythonError("try/except is not allowed in batch mode")

    def visit_With(self, node: ast.With) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        raise RestrictedPythonError("control flow is not allowed in batch mode")

    def visit_Pass(self, node: ast.Pass) -> None:
        raise RestrictedPythonError("only canonical Backend capability calls are allowed")

    def visit_Name(self, node: ast.Name) -> None:
        raise RestrictedPythonError("local variable dataflow is not allowed in batch mode")

    def visit_Attribute(self, node: ast.Attribute) -> None:
        raise RestrictedPythonError(
            "only canonical Backend capability calls are allowed",
            unsafe_attempt=(
                _attribute_root_name(node) in CAPABILITIES
                or _attribute_root_name(node) in UNSAFE_MODULE_NAMES
                or _has_private_access(node)
            ),
        )

    def visit_BinOp(self, node: ast.BinOp) -> None:
        raise RestrictedPythonError("local computation is not allowed in batch mode")

    visit_BoolOp = visit_BinOp
    visit_Compare = visit_BinOp
    visit_Subscript = visit_BinOp
    visit_UnaryOp = visit_BinOp
    visit_Lambda = visit_BinOp
    visit_ListComp = visit_BinOp
    visit_SetComp = visit_BinOp
    visit_DictComp = visit_BinOp
    visit_GeneratorExp = visit_BinOp

    def visit_Import(self, node: ast.Import) -> None:
        raise RestrictedPythonError("only canonical Backend capability calls are allowed", unsafe_attempt=True)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        raise RestrictedPythonError("only canonical Backend capability calls are allowed", unsafe_attempt=True)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        raise RestrictedPythonError("local computation is not allowed in batch mode")

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_ClassDef = visit_FunctionDef
    visit_Raise = visit_FunctionDef
    visit_Yield = visit_FunctionDef
    visit_YieldFrom = visit_FunctionDef

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id == "finish":
            if not (
                len(node.args) == 1
                and not node.keywords
                and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == "done"
            ):
                raise RestrictedPythonError('completion must be exactly finish("done")')
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            namespace = node.func.value.id
            if node.func.attr not in CAPABILITIES.get(namespace, set()):
                if node.func.attr in LOCAL_COMPUTATION_METHODS:
                    raise RestrictedPythonError("local computation is not allowed in batch mode")
                raise RestrictedPythonError(
                    "only canonical Backend capability calls are allowed",
                    unsafe_attempt=(
                        namespace in CAPABILITIES
                        or namespace in UNSAFE_MODULE_NAMES
                        or namespace.startswith("_")
                        or node.func.attr.startswith("_")
                    ),
                )
        elif isinstance(node.func, ast.Name):
            raise RestrictedPythonError(
                "only canonical Backend capability calls are allowed",
                unsafe_attempt=(node.func.id in UNSAFE_FUNCTION_NAMES or node.func.id.startswith("_")),
            )
        else:
            raise RestrictedPythonError(
                "only canonical Backend capability calls are allowed",
                unsafe_attempt=_has_private_access(node.func) if isinstance(node.func, ast.AST) else False,
            )

        if isinstance(node.func, ast.Name) and node.func.id == "finish":
            return
        operation = node.func.attr
        names = ARGUMENT_ORDER[operation]
        if len(node.args) > len(names):
            raise RestrictedPythonError("too many positional arguments")
        seen = set(names[:len(node.args)])
        for value in node.args:
            self.visit_literal(value)
        for keyword in node.keywords:
            if keyword.arg is None:
                raise RestrictedPythonError("expanded keyword arguments are not allowed")
            if keyword.arg in seen:
                raise RestrictedPythonError(f"duplicate argument: {keyword.arg}")
            seen.add(keyword.arg)
            self.visit_literal(keyword.value)

    def visit_literal(self, node: ast.AST) -> None:
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (str, int, bool, type(None))):
                raise RestrictedPythonError("only literal argument values are allowed in batch mode")
            return
        if isinstance(node, (ast.List, ast.Tuple)):
            for element in node.elts:
                self.visit_literal(element)
            return
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if not isinstance(key, ast.Constant):
                    raise RestrictedPythonError("only literal argument values are allowed in batch mode")
                self.visit_literal(key)
                self.visit_literal(value)
            return
        raise RestrictedPythonError("local computation is not allowed in batch mode")


def _literal_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal_value(value) for value in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_literal_value(value) for value in node.elts)
    if isinstance(node, ast.Dict):
        return {_literal_value(key): _literal_value(value) for key, value in zip(node.keys, node.values)}
    raise RestrictedPythonError("only literal argument values are allowed in batch mode")


def _operation_and_arguments(node: ast.Call) -> tuple[str, dict[str, Any]]:
    operation = node.func.attr
    names = ARGUMENT_ORDER[operation]
    if len(node.args) > len(names):
        raise RestrictedPythonError("too many positional arguments")
    arguments = {name: _literal_value(value) for name, value in zip(names, node.args)}
    for keyword in node.keywords:
        if keyword.arg in arguments:
            raise RestrictedPythonError(f"duplicate argument: {keyword.arg}")
        arguments[keyword.arg] = _literal_value(keyword.value)
    return operation, arguments


def _batch_response(index: int, operation: str, arguments: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    item: dict[str, Any] = {
        "index": index,
        "name": operation,
        "arguments": arguments,
        "ok": response.get("ok", False),
        "status": response.get("status", "error"),
    }
    if "result" in response:
        item["result"] = response["result"]
    if "error" in response:
        item["error"] = response["error"]
    return item


def execute_code(source: str, backend: Backend, action_id: str) -> ActionResult:
    try:
        if not isinstance(source, str) or len(source) > 16384:
            raise RestrictedPythonError("program is too large")
        fences = _python_fences(source)
        if len(fences) > 1:
            raise RestrictedPythonError("expected at most one Python code fence")
        if fences and _STANDALONE_FINISH_CALL.search(_strip_fenced_code(source)):
            raise RestrictedPythonError("finish cannot appear outside the program")
        tree = ast.parse(_extract_program(source), mode="exec")
        if len(list(ast.walk(tree))) > 500:
            raise RestrictedPythonError("program AST is too large")
        Validator().visit(tree)
        finish_calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "finish"
        ]
        if len(finish_calls) > 1:
            raise RestrictedPythonError("multiple finish calls are not allowed")
        if finish_calls:
            only_statement = (
                len(tree.body) == 1
                and isinstance(tree.body[0], ast.Expr)
                and tree.body[0].value is finish_calls[0]
            )
            if not only_statement:
                raise RestrictedPythonError("finish must be the only statement")
            return ActionResult(
                "finish",
                json.dumps({"status": "finish", "operations": []}, sort_keys=True),
            )
    except (SyntaxError, RestrictedPythonError) as exc:
        return ActionResult(
            "invalid", _error_observation(VALIDATION_ERROR_TYPE, str(exc), 0), [],
            getattr(exc, "unsafe_attempt", False),
        )

    responses: list[dict[str, Any]] = []
    for index, statement in enumerate(tree.body, 1):
        operation, arguments = _operation_and_arguments(statement.value)
        response = backend.execute(operation, arguments, action_id)
        responses.append(_batch_response(index, operation, arguments, response))
    return ActionResult("ok", _batch_observation(responses), responses)


def execute_action(tool_calls: list[dict[str, Any]], backend: Backend, action_id: str) -> ActionResult:
    try:
        if not isinstance(tool_calls, list) or len(tool_calls) != 1:
            raise ValueError("expected exactly one restricted Python tool call")
        tool_call = tool_calls[0]
        if not isinstance(tool_call, dict):
            raise ValueError("tool call must be an object")
        if tool_call.get("type") != "function":
            raise ValueError("expected a function tool call")
        function = tool_call.get("function")
        if not isinstance(function, dict):
            raise ValueError("function must be an object")
        if function.get("name") != RESTRICTED_PYTHON_TOOL_NAME:
            raise ValueError(f"wrong envelope tool: {function.get('name', '<missing>')}")
        raw_arguments = function.get("arguments")
        if not isinstance(raw_arguments, str):
            raise ValueError("arguments must be JSON text")
        arguments = json.loads(raw_arguments)
        if not isinstance(arguments, dict):
            raise ValueError("arguments must be an object")
        if set(arguments) != {"code"}:
            raise ValueError("envelope arguments must contain only code")
        if not isinstance(arguments["code"], str):
            raise ValueError("code must be a string")
        return execute_code(arguments["code"], backend, action_id)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return ActionResult("invalid", _error_observation(ENVELOPE_ERROR_TYPE, str(exc), 0))
