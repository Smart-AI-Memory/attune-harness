"""New examples for the frozen paired citation comparison."""
import json
from pathlib import Path
from baseline import old

factory = old.previous.load_module('citation_fixture_factory', old.ROOT / 'experiments/memory_sorter/make_cases.py')
fact, source, case = factory.fact, factory.source, factory.case

C = [
    case('capture', 'Remember this accepted update-writing preference using the granted new node ID.', [],
         [source('P10', 'State the outcome before describing the sequence of events.')],
         'capture', 'update', 'Create new-7 as a cedar preference with P10. No cost, speed or rationale invention.', create_ids=['new-7']),
    case('condition', 'Apply the accepted ordinary-runner correction while retaining the signed-run exception.',
         [fact('normal', 'Use Slate for ordinary runs.', ['P20']), fact('signed', 'Signed runs must use Slate.', ['P21'])],
         [source('P20', 'Use Slate for ordinary runs.', 'Previous accepted choice replaced by P22.'),
          source('P21', 'Signed runs must use Slate.'),
          source('P22', 'Prefer Willow for ordinary runs only if execution logs are retained.', 'Accepted correction of P20; signed-run exception stays in force.')],
         'amend', 'update', 'Ordinary Willow is conditional on retained execution logs; signed Slate mandatory. Fact refs P22/P21; top refs must include P22 supporting the correction, not only old P20.'),
    case('distinct', 'Consolidate genuinely duplicate notification preferences, if any; preserve project conditions.',
         [fact('one', 'Send notices on working days at 16:00.', ['P30']), fact('two', 'Send notices every day at 16:00.', ['P31'], scope='elm')],
         [source('P30', 'Send notices on working days at 16:00.'), source('P31', 'Send notices every day at 16:00.', scope='elm')],
         'retain', 'no_change', 'Preserve both exact snapshots, kinds, scopes and refs. Distinct project and day condition; cite P30 and P31 for comparison. No owner choice needed.', scopes=['cedar', 'elm'], remove_ids=['two']),
    case('consolidate', 'Fold the duplicate normal-notification rule into canonical channel; retain the emergency exception.',
         [fact('channel', 'Send normal notifications by email.', ['P40']), fact('copy', 'Normal notifications go by email.', ['P41']), fact('emergency', 'Emergency notifications require a phone call.', ['P42'])],
         [source('P40', 'Send normal notifications by email.'), source('P41', 'Normal notifications go by email.'), source('P42', 'Emergency notifications require a phone call.')],
         'consolidate', 'update', 'Remove copy; canonical email retains P40 and P41; phone-call exception retains P42. Top references must support duplicate equivalence with P40/P41.', remove_ids=['copy']),
    case('forget_all', 'Forget both temporary notes in this captured collection, as requested; produce a candidate only.',
         [fact('temp-a', 'Temporary rehearsal is at 10:00.', ['P50'], 'note'), fact('temp-b', 'Temporary room code is room-C.', ['P51'], 'note')],
         [source('P50', 'Temporary rehearsal is at 10:00.', 'Temporary note.'), source('P51', 'Temporary room code is room-C.', 'Temporary note.'), source('P52', 'Forget both temporary notes temp-a and temp-b. No other memories are part of this request.')],
         'forget', 'update', 'Resulting facts must be empty and version advanced by host. Top references must include P52 for the forgetting decision; content provenance alone is insufficient. No actual durable deletion claim.', remove_ids=['temp-a', 'temp-b']),
    case('kind', 'Classify this saved observation as a lesson, preserving all other fields exactly.',
         [fact('ordering', 'The retry preserved item ordering in this one replay.', ['P60'], 'note')],
         [source('P60', 'The retry preserved item ordering in this one replay.', 'Observed result, not a general guarantee.'), source('P61', 'Keep that observation as a lesson without making it a universal rule.')],
         'classify', 'update', 'Only note to lesson changes. Fact still cites P60; decision evidence must include P61. Do not invent universal reliability.', classify_ids=['ordering']),
    case('absent', 'Reconcile the current interchange-format memory with the finalized replacement decision.',
         [fact('format', 'Use JSON for interchange.', ['P70'])],
         [source('P70', 'Use JSON for interchange.', 'Earlier accepted choice.'), source('P71', 'The finalized replacement choice is in decision-bundle-m2.', 'That attachment has not been supplied.'), source('P72', 'Perhaps try CSV.', 'Unaccepted suggestion, not the finalized attachment.')],
         'amend', 'needs_evidence', 'Request decision-bundle-m2. Cite P71 for the absence/decision-reference claim; never cite attachment filename as source ID. No inferred CSV, reaffirmed JSON or request to choose again.'),
    case('choice', 'Record the replacement cache choice when settled and identify the current next step.',
         [fact('cache', 'Use Rowan for the cache.', ['P80'])],
         [source('P80', 'Use Rowan for the cache.', 'Old accepted choice.'), source('P81', 'We will replace Rowan with either Ash or Fir. I have not selected one and the choice remains mine.')],
         'amend', 'needs_decision', 'Request the owner choice Ash versus Fir with P81 support. Keep old record unmodified without reaffirming it. No missing-document request or choice on owner behalf.'),
]
for c in C:
    c['input']['record']['version'] = 31

if __name__ == '__main__':
    with Path(__file__).with_name('cases.json').open('x', encoding='utf-8') as handle:
        json.dump(C, handle, indent=2, ensure_ascii=False)
        handle.write('\n')
