"""Pure projections of already validated funding evidence; never grant authority."""

import copy
import json


def summaries(record):
    seen, result = set(), []

    def visit(value):
        if isinstance(value, dict):
            funding = value.get('funding')
            if isinstance(funding, dict) and funding.get('profile') == 'participant-funding-v1':
                usage = value.get('usage')
                identity = (value.get('result') or {}).get('identity') or {}
                usage = usage or identity.get('usage')
                item = {'funding': copy.deepcopy(funding), 'usage': copy.deepcopy(usage)}
                key = json.dumps(funding, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    result.append(item)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(record)
    return result


def lines(items):
    result = []
    for item in items:
        funding, usage = item['funding'], item.get('usage') or {}
        def count(name):
            return str(usage[name]) if usage.get(name) is not None else 'unknown'
        result.extend([
            f"{funding['participant_id']}: {funding['requested']} requested; "
            f"{funding['observed']} observed; {funding['state']} ({funding['basis']}); "
            f"dispatch {funding['dispatch_outcome']}; attempt {funding['attempt']}",
            f"Reported tokens: input {count('input_tokens')}, output {count('output_tokens')}, "
            f"cached input {count('cached_input_tokens')} (included in input). "
            'Billed cost and remaining balance: unknown.',
        ])
    return result
