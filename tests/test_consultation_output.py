"""Readable views preserve retained data and explicit execution authority."""
# qualify: platform

import copy
import shlex
import unittest

from attune_harness import consultation_output as renderer


def prepared():
    return {'operation': 'roundtable', 'status': 'prepared', 'contract_digest': 'c' * 64,
            'checkpoint_digest': 'd' * 64, 'record_path': '/tmp/a run/record.json',
            'contract': {'configuration': {'question': 'Inspect only', 'participants': {
                'critic': {'identity': {'provider': 'other', 'model': 'explicit-model'},
                           'adapter': 'command', 'timeout': 10}}},
                'snapshot': {'files': {'x.py': {'sha256': 'a' * 64, 'text': 'secret = "é"\r\n'}}},
                'budget': {'max_calls': 1, 'automatic_retries': 0}}, 'answers': []}


class ConsultationOutputPreparationTests(unittest.TestCase):
    def test_prepare_omits_frozen_source_but_preserves_digests_and_byte_size(self):
        record = prepared()
        out = renderer.markdown(record, view='prepare')
        self.assertNotIn('secret =', out)
        self.assertIn('SHA-256 ' + 'a' * 64, out)
        self.assertIn(str(len('secret = "é"\r\n'.encode())) + ' bytes', out)
        self.assertIn('c' * 64, out)
        self.assertIn('d' * 64, out)

    def test_accept_command_quotes_run_path_without_execution_grants(self):
        out = renderer.markdown(prepared(), view='prepare')
        command = next(line for line in out.splitlines() if line.startswith('attune-harness '))
        self.assertEqual(shlex.split(command), ['attune-harness', 'roundtable', 'run',
                                               '--accept', 'c' * 64, '--', '/tmp/a run'])
        self.assertNotIn('--allow-external', command)
        self.assertNotIn('--allow-native', command)

    def test_no_record_mutation_or_dispatch(self):
        record = prepared()
        before = copy.deepcopy(record)
        renderer.markdown(record, view='prepare')
        self.assertEqual(record, before)

    def test_failed_turn_preserves_unknown_effects_and_unreported_identity(self):
        record = prepared(); record['status'] = 'failed'
        record['answers'] = [{'round': 1, 'participant': 'critic', 'status': 'failed',
                              'identity': {'authenticated_model': False}, 'answer': None,
                              'error': {'effects': 'unknown', 'detail': 'Timed out'}}]
        out = renderer.markdown(record, view='status')
        self.assertIn('**Turn status:** failed', out)
        self.assertIn('**Reported identity:** not recorded', out)
        self.assertIn('unknown', out)
        self.assertIn('Timed out', out)

    def test_completed_answer_and_reported_identity_are_distinct_from_authority(self):
        record = prepared(); record['status'] = 'completed'
        record['answers'] = [{'round': 1, 'participant': 'critic', 'status': 'completed',
                              'identity': {'configured': {'provider': 'other', 'model': 'explicit'},
                                           'reported': {'provider': 'other', 'reported_models': ['generic']},
                                           'authenticated_model': False},
                              'answer': {'verdict': 'approve', 'summary': 'Claim only', 'evidence': []}, 'error': None}]
        out = renderer.markdown(record, view='status')
        self.assertIn('**Verdict:** approve', out)
        self.assertIn('generic', out)
        self.assertIn('**Authenticated model:** False', out)
        self.assertIn('grant no execution authority', out)

    def test_assessed_citation_uses_supplied_frozen_context_and_safe_fence(self):
        record = prepared()
        view = {'operation': 'roundtable', 'status': 'completed', 'claims': [
            {'round': 1, 'participant': 'critic', 'citation': 0, 'path': 'x.py', 'line': 2,
             'support': 'rejected', 'detail': '<script>not authority</script>',
             'source': [{'line': 1, 'text': '````'}, {'line': 2, 'text': 'frozen bytes'}],
             'assessments': [{'decision': 'rejected', 'note': 'Source contradicts claim'}]}]}
        out = renderer.markdown(view, view='evidence', retained=record)
        self.assertIn('**Support:** rejected (advisory host assessment)', out)
        self.assertIn('`````text\n1: ````\n2: frozen bytes\n`````', out)
        self.assertNotIn('<script>', out)
        self.assertIn('Source contradicts claim', out)

    def test_hostile_markdown_is_literal_instead_of_a_link_or_heading(self):
        record = prepared(); record['contract']['configuration']['question'] = '\n# [click](javascript:evil) <img>'
        out = renderer.markdown(record, view='prepare')
        self.assertNotIn('\n# [click]', out)
        self.assertNotIn('<img>', out)
        self.assertIn('\\[click\\]', out)

    def test_refusal_golden_remains_visible_without_a_contract(self):
        out = renderer.markdown({'operation': 'source-review', 'status': 'refused',
                                 'error': {'type': 'ValueError', 'detail': 'Wrong owner'}}, view='status')
        self.assertEqual(out, '## source\\-review: status\n\n**Status:** refused\n\n'
                         'Retained model claims and this view grant no execution authority.\n\n'
                         '**Error (ValueError):** Wrong owner\n')

    def test_terminal_controls_in_untrusted_text_are_visible_without_execution(self):
        record = prepared(); record['contract']['configuration']['question'] = '\x1b[31mred'
        out = renderer.markdown(record, view='prepare')
        self.assertNotIn('\x1b', out)
        self.assertIn('x1b', out)
        self.assertEqual(renderer._block('\x1b[2J'), '```text\n\\x1b[2J\n```')

    def test_completed_failed_and_assessed_citation_golden_views(self):
        record = {'operation': 'roundtable', 'status': 'completed',
                  'contract': {'configuration': {'participants': {}},
                               'snapshot': {'files': {'x.py': {'text': 'frozen\n'}}}},
                  'answers': [{'round': 0, 'participant': 'critic', 'status': 'completed',
                               'identity': {'configured': {'provider': 'other', 'model': 'explicit'},
                                            'reported': {'provider': 'other', 'reported_models': ['generic']},
                                            'authenticated_model': False},
                               'answer': {'verdict': 'uncertain', 'summary': 'A claim', 'evidence': []},
                               'error': None}]}
        completed = ('## roundtable: status\n\n**Status:** completed\n\n'
                     'Retained model claims and this view grant no execution authority.\n\n'
                     '### Round 0 / critic\n\n**Turn status:** completed\n'
                     '**Configured identity:** other/explicit\n**Reported identity:** other: generic\n'
                     '**Authenticated model:** False\n**Verdict:** uncertain\n\nA claim\n\n'
                     'No retained citations.\n')
        self.assertEqual(renderer.markdown(record, view='status'), completed)
        failed = copy.deepcopy(record)
        failed['status'] = failed['answers'][0]['status'] = 'failed'
        failed['answers'][0]['answer'] = None
        failed['answers'][0]['error'] = {'detail': 'Timed out', 'effects': 'unknown'}
        self.assertEqual(renderer.markdown(failed, view='status'),
                         completed.replace('completed', 'failed').replace(
                             '**Verdict:** uncertain\n\nA claim',
                             '\n**Turn error:** detail=Timed out; effects=unknown'))
        evidence = {'operation': 'roundtable', 'status': 'completed', 'claims': [
            {'round': 0, 'participant': 'critic', 'citation': 0, 'path': 'x.py', 'line': 1,
             'support': 'supported', 'detail': 'A claim', 'source': [{'line': 1, 'text': 'frozen'}],
             'assessments': [{'decision': 'supported', 'note': 'Checked locally'}]}]}
        expected = completed.replace('roundtable: status', 'roundtable: evidence').replace(
            'No retained citations.\n',
            '### Citation 0 / round 0 / critic\n\n**Source:** x\\.py:1\n'
            '**Support:** supported (advisory host assessment)\n\nA claim\n\n'
            '```text\n1: frozen\n```\n\n**Assessment:** supported: Checked locally\n')
        self.assertEqual(renderer.markdown(evidence, view='evidence', retained=record), expected)

    def test_unassessed_citation_is_not_attributed_to_a_host_assessment(self):
        evidence = {'operation': 'roundtable', 'status': 'completed', 'claims': [
            {'round': 0, 'participant': 'critic', 'citation': 0, 'path': 'x.py', 'line': 1,
             'support': 'unchecked', 'detail': 'An untested claim',
             'source': [{'line': 1, 'text': 'frozen'}], 'assessments': []}]}
        out = renderer.markdown(evidence, view='evidence', retained=prepared())
        self.assertIn('**Support:** unchecked (no host assessment recorded)', out)
        self.assertNotIn('advisory host assessment', out)

    def test_all_c1_controls_are_visible_instead_of_terminal_controls(self):
        controls = ''.join(chr(value) for value in range(128, 160))
        expected = ''.join('\\x' + format(value, '02x') for value in range(128, 160))
        self.assertEqual(renderer._block(controls), '```text\n' + expected + '\n```')
        record = prepared(); record['contract']['configuration']['question'] = controls
        out = renderer.markdown(record, view='prepare')
        self.assertFalse(any(char in out for char in controls))


if __name__ == '__main__':
    unittest.main()
