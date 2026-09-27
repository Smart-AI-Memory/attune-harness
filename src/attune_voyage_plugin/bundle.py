"""Create an unsigned, deterministic Voyage bundle; acceptance stays with the user."""

import argparse
import json
from pathlib import Path
import zipfile


SOURCES = ('__init__.py', 'common.py', 'provider.py', 'embed.py', 'rerank.py', 'index.py')
SKILL = ('# Voyage plugin\n\nSigned run tools for bounded Voyage embeddings, reranking and local '
         'LanceDB materialization. Select and accept this bundle explicitly before use.\n')
GRANTS = {'secrets': ['VOYAGE_API_KEY'], 'paths': ['index_staging'], 'scratch': True,
          'time': 300, 'output': {'result': 1_048_576, 'diagnostics': 8192}}
DECLARES = {'imports': ['voyageai', 'lancedb'], 'network': ['api.voyageai.com'],
            'reads': [], 'writes': [], 'subprocess': False, 'vendored': []}


def build(output: Path):
    """Never overwrite an existing bundle directory or sign/accept it automatically."""
    output.mkdir()  # Exclusive; a failed build remains inspectable.
    root = Path(__file__).parent
    with zipfile.ZipFile(output / 'code.zip', 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCES:
            info = zipfile.ZipInfo(f'attune_voyage_plugin/{name}', date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (root / name).read_bytes())
    def tool(entry):
        return {'binding': 'run', 'entry': f'attune_voyage_plugin.{entry}',
                'input_schema': {'type': 'object'}, 'output_schema': {'type': 'object'}}
    manifest = {'schema_version': 1, 'id': 'voyage', 'version': '1.0.0', 'skill': 'SKILL.md',
                'code': 'code.zip', 'tools': {role: tool(role) for role in ('embed', 'rerank', 'index')},
                'grants': GRANTS, 'declares': DECLARES}
    (output / 'SKILL.md').write_text(SKILL, encoding='utf-8')
    (output / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    from attune_harness.extensions import discover
    return discover(output / 'manifest.json')['artifact_digest']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps({'bundle': str(args.output.absolute()), 'artifact_digest': build(args.output)}))


if __name__ == '__main__':
    main()
