"""Strict host-owned materialization of selected top-level Python bodies."""

import ast
import copy
import io
import tokenize

from . import repair


def _parse(raw, symbol):
    if not isinstance(raw, bytes) or raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("Function body source requires UTF-8 without BOM or CR")
    if not raw.endswith(b"\n") or b"\t" in raw:
        raise ValueError("Function body source requires LF termination and no tabs")
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
    except SyntaxError as exc:
        raise ValueError("Invalid Python source encoding") from exc
    if encoding.lower().replace("_", "-") not in ("utf-8", "utf-8-sig"):
        raise ValueError("Function body source must declare UTF-8")
    text = raw.decode("utf-8")
    try:
        tree = ast.parse(text)
        compile(tree, "<function-body>", "exec")
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise ValueError("Function body source must parse and compile") from exc
    nodes = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == symbol
    ]
    if len(nodes) != 1:
        raise ValueError("Expected exactly one selected top-level function")
    node = nodes[0]
    if not node.body:
        raise ValueError("Selected function needs a multiline body")
    first = node.body[0]
    start_line = min(
        [first.lineno]
        + [decorator.lineno for decorator in getattr(first, "decorator_list", [])]
    )
    lines = raw.splitlines(keepends=True)
    if first.col_offset != 4 or not lines[start_line - 1].startswith(b"    "):
        raise ValueError("Selected function needs four-space multiline indentation")
    start = sum(map(len, lines[: start_line - 1]))
    end = sum(map(len, lines[: node.end_lineno]))
    return tree, node, start, end


def _outside(tree, node):
    try:
        frozen = copy.deepcopy(tree)
        frozen.body[tree.body.index(node)].body = [ast.Pass()]
        return ast.dump(frozen, include_attributes=False)
    except RecursionError as exc:
        raise ValueError("Function body AST exceeds supported depth") from exc


def validate_binding(path, binding, before):
    if not path.endswith(".py") or path not in before:
        raise ValueError("Function body targets must be existing Python files")
    if not isinstance(binding, dict) or set(binding) != {"symbol", "source"}:
        raise ValueError("Invalid function body binding")
    if not isinstance(binding["symbol"], str) or not binding["symbol"].isidentifier():
        raise ValueError("Invalid function body symbol")
    source = binding["source"]
    if not isinstance(source, str) or len(source.encode("utf-8")) > repair.MAX_FILE:
        raise ValueError("Invalid retained function source")
    raw = source.encode("utf-8")
    if repair.sha(raw) != before[path]["sha256"]:
        raise ValueError("Retained function source differs from its preimage")
    _parse(raw, binding["symbol"])


def validate_manifest(extension, allowed, before):
    if not isinstance(extension, dict) or set(extension) != {"version", "bindings"}:
        raise ValueError("Invalid function_bodies manifest")
    if (
        type(extension["version"]) is not int
        or extension["version"] != 1
        or not isinstance(extension["bindings"], dict)
    ):
        raise ValueError("Unsupported function_bodies manifest")
    if set(extension["bindings"]) != set(allowed):
        raise ValueError("Function body bindings must exactly match allowed paths")
    for path, binding in extension["bindings"].items():
        validate_binding(path, binding, before)


def _reject_dedented_comments(body):
    try:
        tokens = tokenize.generate_tokens(io.StringIO(body).readline)
        for token in tokens:
            if token.type == tokenize.COMMENT:
                line = token.line
                prefix = line[: token.start[1]]
                if len(prefix) < 4 or prefix[:4] != "    ":
                    raise ValueError(
                        "Function body comment escaped four-space indentation"
                    )
    except (tokenize.TokenError, IndentationError) as exc:
        raise ValueError("Invalid function body tokens") from exc


def materialize(plan, path, body):
    binding = plan["function_bodies"]["bindings"][path]
    original = binding["source"].encode("utf-8")
    tree, node, start, end = _parse(original, binding["symbol"])
    if (
        not isinstance(body, str)
        or not body
        or not body.endswith("\n")
        or "\r" in body
        or "\t" in body
    ):
        raise ValueError("Body must be nonempty LF-terminated text without CR or tabs")
    encoded = body.encode("utf-8")
    if len(encoded) > repair.MAX_FILE:
        raise ValueError("Function body exceeds the UTF-8 byte limit")
    _reject_dedented_comments(body)
    candidate = original[:start] + encoded + original[end:]
    if len(candidate) > repair.MAX_FILE:
        raise ValueError("Materialized file exceeds the UTF-8 byte limit")
    new_tree, new_node, _, _ = _parse(candidate, binding["symbol"])
    if _outside(tree, node) != _outside(new_tree, new_node):
        raise ValueError("Function body escaped its accepted boundary")
    if candidate == original:
        raise ValueError("Function body is unchanged")
    return candidate.decode("utf-8")


def validate_file(plan, item):
    """Recheck a full-file operation at every effect/recovery boundary."""
    if "function_bodies" not in plan:
        return
    path = item.get("path")
    if (
        path not in plan["function_bodies"]["bindings"]
        or item.get("kind") != "replacement"
        or item.get("before_sha256") != plan["before"][path]["sha256"]
    ):
        raise ValueError("Function body manifest permits replacements only")
    binding = plan["function_bodies"]["bindings"][path]
    original = binding["source"].encode("utf-8")
    candidate = item.get("text")
    if not isinstance(candidate, str):
        raise ValueError("Function body operation needs full UTF-8 text")
    raw = candidate.encode("utf-8")
    if len(raw) > repair.MAX_FILE:
        raise ValueError("Materialized file exceeds the UTF-8 byte limit")
    old_tree, old_node, old_start, old_end = _parse(original, binding["symbol"])
    prefix, suffix = original[:old_start], original[old_end:]
    if (
        not raw.startswith(prefix)
        or not raw.endswith(suffix)
        or len(raw) < len(prefix) + len(suffix)
    ):
        raise ValueError("Full file exceeds the accepted function body boundary")
    body_end = len(raw) - len(suffix) if suffix else len(raw)
    body = raw[len(prefix) : body_end].decode("utf-8")
    if materialize(plan, path, body) != candidate:
        raise ValueError("Full file exceeds the accepted function body boundary")
