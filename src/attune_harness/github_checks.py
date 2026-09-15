"""Read-only conversion of GitHub REST check-run exports into triage suggestions.

The caller obtains authenticated REST data and supplies the expected repository
and exact revision. This is not an HTTP webhook receiver or a signature verifier.
"""
import re

from .operations import triage


def check_suggestions(payload, *, repository, revision, handled_keys=(), max_attempts=2):
    if not isinstance(repository,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('Expected owner/repository')
    if not isinstance(revision,str) or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}',revision):
        raise ValueError('Expected full lowercase commit SHA')
    if not isinstance(payload,dict) or not isinstance(payload.get('check_runs'),list):
        raise ValueError('Expected a GitHub check_runs REST export')
    runs=payload['check_runs']
    if type(payload.get('total_count')) is not int or payload['total_count']!=len(runs):
        raise ValueError('Incomplete or paginated export; collect all check runs first')
    results=[];seen=set()
    for run in runs:
        if not isinstance(run,dict) or run.get('head_sha')!=revision:
            raise ValueError('Check result belongs to a different revision')
        rid=run.get('id');app=run.get('app',{})
        if type(rid) is not int or rid<1 or rid in seen or type(app.get('id')) is not int or app['id']<1:
            raise ValueError('Missing or duplicate check/app identity')
        seen.add(rid)
        if not isinstance(run.get('name'),str) or not run['name'].strip():raise ValueError('Missing check name')
        status=run.get('status');conclusion=run.get('conclusion')
        if status in ('queued','in_progress','waiting','pending','requested'):
            if conclusion is not None:raise ValueError('Nonterminal check has a conclusion')
            normalized='pending'
        elif status=='completed':
            normalized={'success':'passed','failure':'failed','timed_out':'failed',
                        'cancelled':'cancelled'}.get(conclusion,'unknown')
        else:raise ValueError('Unknown GitHub check status')
        event={'repository':repository,'revision':revision,'check':str(app['id'])+':'+run['name'],
            'run_id':str(rid),'status':normalized,'failure_kind':'unknown',
            'effects':'unknown' if conclusion in ('timed_out','cancelled') else 'none','attempts':0}
        results.append({'event':event,'suggestion':triage(event,handled_keys=handled_keys,max_attempts=max_attempts)})
    return {'schema_version':1,'repository':repository,'revision':revision,'checks':results,
            'all_checks_passed':bool(results) and all(r['event']['status']=='passed' for r in results),
            'repair_verified':False,'note':'These are the exported checks, not proof that every required check exists. No dispatch or GitHub write performed.'}
