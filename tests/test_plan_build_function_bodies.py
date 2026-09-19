"""Behavioral boundaries of the offline function-body replacement prototype."""
import importlib.util
from pathlib import Path
import sys
import unittest

PATH = Path(__file__).resolve().parents[1] / 'experiments/plan_build/function_body_replacements.py'
SPEC = importlib.util.spec_from_file_location('body_boundary_under_test', PATH)
body = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = body
SPEC.loader.exec_module(body)


class FunctionBodyTests(unittest.TestCase):
    source = '# café\nVALUE = 7\n\n@decorate\ndef target(value: int = 3) -> int:\n    """original docstring"""\n    return value - 1\n\n# untouched tail\ndef other():\n    return VALUE\n'.encode()

    def binding(self, source=None):
        return body.bind(source or self.source, 'src/subject.py', 'target')

    def test_multiline_unicode_body_preserves_every_other_byte(self):
        proposal = '    """naïve\ntext at column zero inside a string\n    """\n    return value + 1\n'
        candidate = body.replace_body(self.source, self.binding(), proposal)
        self.assertEqual(body.extract_body(candidate, 'target'), proposal)
        self.assertTrue(all(body.preservation(self.source, candidate, 'target').values()))

    def test_nested_decorated_first_statement_is_kept_in_body(self):
        candidate = body.replace_body(self.source, self.binding(), '    @decorate\n    def nested():\n        return 3\n    return nested()\n')
        self.assertTrue(body.extract_body(candidate, 'target').startswith('    @decorate\n'))

    def test_stale_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Stale actual source'):
            body.replace_body(self.source + b'# concurrent edit\n', self.binding(), '    return 3\n')

    def test_dedented_code_cannot_edit_the_module(self):
        for tail in ('VALUE = 99\n', 'def extra():\n    return 4\n', 'def target(value):\n    return 4\n'):
            with self.subTest(tail=tail), self.assertRaises((ValueError, SyntaxError)):
                body.replace_body(self.source, self.binding(), '    return 3\n\n' + tail)

    def test_triple_quote_cannot_swallow_following_definitions(self):
        with self.assertRaises((ValueError, SyntaxError)):
            body.replace_body(self.source, self.binding(), '    return 3\n    """\n')

    def test_wrong_file_and_symbol_are_rejected(self):
        with self.assertRaises(ValueError):
            body.bind(self.source, '../outside.py', 'target')
        with self.assertRaises(ValueError):
            body.bind(self.source, 'src/subject.py', 'missing')
        forged = body.Binding('src/other.py', 'target', self.binding().before_sha256)
        with self.assertRaises(ValueError):
            body.replace_body(self.source, forged, '    return 3\n')

    def test_duplicate_and_inline_targets_are_rejected(self):
        for source in (b'def target(): return 1\n', b'def target():\n    return 1\ndef target():\n    return 2\n'):
            with self.subTest(source=source), self.assertRaises(ValueError):
                self.binding(source)

    def test_invalid_python_is_not_repaired(self):
        with self.assertRaises(SyntaxError):
            body.replace_body(self.source, self.binding(), '    return (\n')

    def test_unchanged_replacement_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unchanged replacement'):
            body.replace_body(self.source, self.binding(), body.extract_body(self.source, 'target'))

    def test_crlf_out_of_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            self.binding(self.source.replace(b'\n', b'\r\n'))

    def test_full_file_is_not_a_body(self):
        with self.assertRaises((ValueError, SyntaxError)):
            body.replace_body(self.source, self.binding(), self.source.decode())

    def test_wrong_logic_can_still_fit_the_boundary(self):
        candidate = body.replace_body(self.source, self.binding(), '    return value * 100\n')
        self.assertTrue(all(body.preservation(self.source, candidate, 'target').values()))
        # The boundary makes no claim of behavioral correctness.
        self.assertIn(b'return value * 100', candidate)


if __name__ == '__main__':
    unittest.main(verbosity=2)
