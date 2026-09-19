"""Disposable pre-call rule; structural eligibility is not a correctness claim."""

import ast
import hashlib


def route(source, request, artifacts):
    """Read only pre-call source and host-declared evidence; never a reference repair."""
    def result(model, reason):
        return {"model": model, "reason": reason, "blocked": model is None}

    if request.get("source_sha256") != hashlib.sha256(source.encode()).hexdigest():
        return result(None, "missing-or-stale-source-binding")
    if not request.get("expected_behavior") or not request.get("target_symbol") or not request.get("target_path"):
        return result(None, "missing-required-behavior-or-target")
    checks = request.get("required_checks", {})
    if not isinstance(checks, dict) or len(checks) != 2 or any(
        not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h)
        or artifacts.get(p) != h for p, h in checks.items()
    ):
        return result(None, "missing-or-stale-required-checks")
    if request.get("writable_files") != [request.get("target_path")]:
        return result("gpt-5.6-sol", "outside-single-file-profile")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result("gpt-5.6-sol", "source-needs-syntax-repair")
    functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if sum(n.name == request["target_symbol"] for n in functions) != 1:
        return result(None, "missing-or-ambiguous-declared-target")
    if len(functions) != 1:
        return result("gpt-5.6-sol", "unrelated-definitions-to-preserve")
    target = functions[0]
    if not isinstance(target, ast.FunctionDef) or target.decorator_list:
        return result("gpt-5.6-sol", "async-or-decorated-target")
    for node in tree.body:
        if node is target or isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and all(isinstance(t, ast.Name) for t in node.targets):
            continue
        return result("gpt-5.6-sol", "other-module-behavior-to-preserve")
    descendants = [n for statement in target.body for n in ast.walk(statement)]
    complex_nodes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Await,
                     ast.Yield, ast.YieldFrom, ast.Global, ast.Nonlocal, ast.Try,
                     ast.With, ast.AsyncWith, ast.AsyncFor)
    if any(isinstance(n, complex_nodes) for n in descendants):
        return result("gpt-5.6-sol", "outside-bounded-function-profile")
    if sum(isinstance(n, ast.stmt) for n in descendants) > 12:
        return result("gpt-5.6-sol", "more-than-twelve-statements")
    return result("gpt-5.6-luna", "bounded-isolated-function")


def preservation(source, target_symbol):
    """Frozen post-reply oracle: body edits allowed; unrelated AST/interface fixed."""
    tree = ast.parse(source)
    target = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == target_symbol)
    interface = {"kind": type(target).__name__, "args": ast.dump(target.args),
                 "returns": ast.dump(target.returns) if target.returns else None,
                 "decorators": [ast.dump(n) for n in target.decorator_list]}
    outside = [ast.dump(n) for n in tree.body if n is not target]
    return {"interface": interface, "outside": outside}
