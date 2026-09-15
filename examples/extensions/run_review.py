"""Run the installed data-only evidence plugin through a deterministic review."""
import argparse
import json
from importlib.metadata import distribution
from pathlib import Path

from attune_harness.extensions import install, mutate
from attune_harness.review import review
from attune_harness.review_contract import load_registry, review_form

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--work-dir', type=Path, required=True, help='New directory for this local fixture')
args = parser.parse_args()
work = args.work_dir.absolute()
work.mkdir()
root = Path(__file__).resolve().parents[2]
manifest = Path(distribution('attune-harness-evidence-example').locate_file('attune_harness_evidence/extension.json'))
state_dir = work / 'extension-state'
state = install(manifest, state_dir)
state = mutate(state_dir, state['state_digest'], 'enable')
config = work / 'participants.json'
config.write_text(json.dumps({'schema_version': 1, 'extensions': {'evidence': {
    'state_dir': str(state_dir), 'artifact_digest': state['artifact_digest']}}, 'participants': {
    name: {'adapter': 'deterministic', 'tools': ['evidence.search', 'verify'], 'max_turns': 3, 'max_tool_calls': 2}
    for name in ('lead', 'reviewer')}}, indent=2) + '\n', encoding='utf-8')
submission = review_form(load_registry(config))['submission']
submission.update(accepted=True, answers={'objective': 'Review local evidence using the contributed tool',
    'query': 'quartz retention policy', 'document': str(root / 'examples/local-workflow/project/guide.md'),
    'context': str(root / 'examples/local-workflow/context.json'),
    'corpus': str(root / 'examples/local-workflow/project'), 'lead': 'lead', 'reviewer': 'reviewer'})
request = work / 'request.json'
request.write_text(json.dumps(submission, indent=2) + '\n', encoding='utf-8')
result = review(request, config, work / 'run')
assert result['status'] == 'completed', result.get('error')
assert result['document_outcome'] == 'verified' and result['retrieval_outcome'] == 'retrieved'
summary = {key: result[key] for key in ('status', 'record_path', 'document_outcome', 'retrieval_outcome')}
summary.update(artifact_digest=state['artifact_digest'], provider_calls=0,
               extension_calls=sum('extension' in event.get('result', {}) for event in result['events']))
(work / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
print(json.dumps(summary, indent=2))
