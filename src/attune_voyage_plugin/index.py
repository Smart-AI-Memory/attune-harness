"""Signed local LanceDB materialization; never chooses the published destination."""

import json
import os
from pathlib import Path

from .common import digest, request, result


def materialize(staging, arguments):
    if (not isinstance(arguments, dict) or set(arguments) != {'generation', 'row_count', 'rows_digest'}
            or type(arguments['row_count']) is not int or arguments['row_count'] < 0):
        raise ValueError('Invalid Voyage index request')
    source = staging / 'rows.json'
    if source.is_symlink() or source.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Voyage index rows exceed bound or are a symlink')
    rows = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(rows, list) or len(rows) != arguments['row_count'] or digest(rows) != arguments['rows_digest']:
        raise ValueError('Voyage index rows do not match host request')
    if rows:
        import lancedb
        from lancedb.index import FTS
        db = lancedb.connect(str(staging / 'db'))
        table = db.create_table('passages', rows, mode='create')
        table.create_index('text', config=FTS(stem=False, remove_stop_words=False,
                                              ascii_folding=False, max_token_length=256))
        if table.count_rows() != len(rows):
            raise ValueError('Voyage index row count changed')
    return {'row_count': len(rows), 'rows_digest': digest(rows)}


if __name__ == '__main__':
    if 'VOYAGE_API_KEY' in os.environ:
        raise ValueError('Local Voyage index must not receive a paid-provider credential')
    data = request()
    if set(data['paths']) != {'index_staging'}:
        raise ValueError('Voyage index needs only index_staging')
    result(materialize(Path(data['paths']['index_staging']), data['arguments']))
