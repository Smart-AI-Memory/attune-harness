"""Offline prototype: a trusted host binds one top-level function body.

This is a source-edit boundary, not a runtime sandbox. Only LF, UTF-8,
four-space multiline functions are supported. No filesystem writes or providers.
"""
import ast
import copy
from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class Binding:
    path: str
    symbol: str
    before_sha256: str


def _parse(source, symbol):
    if not isinstance(source, bytes) or b'\r' in source or not source.endswith(b'\n'):
        raise ValueError('Expected LF-terminated UTF-8 source bytes')
    text = source.decode('utf-8')
    tree = ast.parse(text)
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.name == symbol]
    if len(nodes) != 1:
        raise ValueError('Expected exactly one accepted top-level function')
    node = nodes[0]
    first = node.body[0]
    line = min([first.lineno] + [d.lineno for d in getattr(first, 'decorator_list', [])])
    lines = source.splitlines(keepends=True)
    if first.col_offset != 4 or not lines[line - 1].startswith(b'    '):
        raise ValueError('Expected a multiline function body with four-space indentation')
    start = sum(map(len, lines[:line - 1]))
    end = sum(map(len, lines[:node.end_lineno]))
    return tree, node, start, end


def _outside(tree, node):
    frozen = copy.deepcopy(tree)
    frozen.body[tree.body.index(node)].body = [ast.Pass()]
    return ast.dump(frozen, include_attributes=False)


def bind(source, path, symbol):
    """Called only with trusted accepted metadata, never worker-selected fields."""
    if path != 'src/subject.py':
        raise ValueError('This replay profile permits only the accepted subject file')
    _parse(source, symbol)
    return Binding(path, symbol, hashlib.sha256(source).hexdigest())


def extract_body(source, symbol):
    """Offline projection from a retained full-file reply; never repairs syntax."""
    _, _, start, end = _parse(source, symbol)
    return source[start:end].decode('utf-8')


def replace_body(current, binding, body):
    """Materialize a body against the actual source and the trusted binding."""
    if binding.path != 'src/subject.py':
        raise ValueError('Unaccepted file target')
    if hashlib.sha256(current).hexdigest() != binding.before_sha256:
        raise ValueError('Stale actual source')
    tree, node, start, end = _parse(current, binding.symbol)
    if not isinstance(body, str) or not body or not body.endswith('\n') or '\r' in body:
        raise ValueError('Expected a nonempty LF-terminated function body')
    encoded = body.encode('utf-8')
    if len(encoded) > 128000:
        raise ValueError('Body exceeds this replay profile')
    candidate = current[:start] + encoded + current[end:]
    new_tree, new_node, _, _ = _parse(candidate, binding.symbol)
    if _outside(tree, node) != _outside(new_tree, new_node):
        raise ValueError('Body escaped its accepted function or changed its interface')
    if candidate == current:
        raise ValueError('Unchanged replacement')
    assert candidate[:start] == current[:start]
    assert candidate[start + len(encoded):] == current[end:]
    return candidate


def preservation(original, candidate, symbol):
    """Independent byte/AST evidence for the inserted region and its context."""
    old_tree, old_node, start, end = _parse(original, symbol)
    new_tree, new_node, new_start, new_end = _parse(candidate, symbol)
    return {
        'prefix_bytes_identical': original[:start] == candidate[:new_start],
        'suffix_bytes_identical': original[end:] == candidate[new_end:],
        'outside_ast_and_interface_identical': _outside(old_tree, old_node) == _outside(new_tree, new_node),
    }
