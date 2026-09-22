"""Offline token counts for one qualified local Llama model and template."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path

PIN = {'name': 'llama3.1:8b',
       'digest': '46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e',
       'server_version': '0.31.1'}
PROFILE_SHA256 = '73892438d8a0c3e3ac85d94d5c77f57beda339f2a9c4e1129ff68faa742af01f'
MAX_PROFILE_BYTES = 4_194_304
# Llama BPE's lexical split; ranks come from the pinned local GGUF vocabulary.
PATTERN = r"(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}{1,3}| ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"


def profile_bytes(show):
    try:
        info = show['model_info']
        value = {'schema_version': 1, 'model_pin': PIN, 'template': show['template'],
                 'tokenizer': {key: info['tokenizer.ggml.' + key] for key in
                               ('model', 'pre', 'bos_token_id', 'eos_token_id', 'tokens', 'token_type')}}
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (KeyError, TypeError) as exc:
        raise ValueError('Incomplete local tokenizer metadata') from exc
    if hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise ValueError('Local tokenizer/template differs from the qualified profile')
    return raw


def export_tokenizer(output):
    """Read existing local metadata; never generate, download, or overwrite."""
    from .ollama import LocalModel, ModelPin, local_request
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    model = LocalModel(ModelPin(**PIN))
    before = model.metadata()
    raw = profile_bytes(local_request('show', {'model': PIN['name'], 'verbose': True}))
    if model.metadata() != before:
        raise ValueError('Model metadata changed during tokenizer export')
    with output.open('xb') as stream:
        stream.write(raw)
    return {'profile': str(output), 'sha256': PROFILE_SHA256, 'model_pin': PIN, 'generation_calls': 0}


class LlamaTokenizer:
    def __init__(self, path, pin):
        if any(getattr(pin, key, None) != value for key, value in PIN.items()):
            raise ValueError('Tokenizer is not qualified for the accepted model/server pin')
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_PROFILE_BYTES + 1)
        if len(raw) > MAX_PROFILE_BYTES or hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
            raise ValueError('Tokenizer file differs from the qualified profile')
        try:
            if importlib.metadata.version('tiktoken') != '0.12.0':
                raise ValueError('Token accounting requires tiktoken 0.12.0; reinstall with: pip install --force-reinstall attune-harness')
            import tiktoken
        except (ImportError, importlib.metadata.PackageNotFoundError) as exc:
            raise ValueError('Token accounting unavailable; tiktoken is missing; reinstall with: pip install --force-reinstall attune-harness') from exc
        tokenizer = json.loads(raw)['tokenizer']
        # Inverse of GGUF/GPT-2's reversible byte-to-Unicode alphabet.
        visible = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
        other = [byte for byte in range(256) if byte not in visible]
        alphabet = {chr(char): byte for char, byte in
                    zip(visible + list(range(256, 256 + len(other))), visible + other)}
        ranks, special = {}, {}
        for rank, (token, kind) in enumerate(zip(tokenizer['tokens'], tokenizer['token_type'])):
            if kind == 1:
                ranks[bytes(alphabet[char] for char in token)] = rank
            else:
                special[token] = rank
        self.encoding = tiktoken.Encoding(name='harness-local-llama3', pat_str=PATTERN,
                                          mergeable_ranks=ranks, special_tokens=special)
        self.pin = pin
        self.identity = {'kind': 'model_tokens', 'profile_sha256': PROFILE_SHA256,
                         'tokenizer': 'tiktoken', 'tokenizer_version': '0.12.0', 'model_pin': dict(PIN)}

    def count(self, prompt, system):
        # Exact text-only template for the hash-qualified model, plus automatic BOS.
        rendered = '<|begin_of_text|>'
        for role, content in [('system', system), ('user', prompt)]:
            if role == 'system' and not content:
                continue
            rendered += f'<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>'
        rendered += '<|start_header_id|>assistant<|end_header_id|>\n\n'
        return len(self.encoding.encode(rendered, allowed_special='all'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New file for the already-installed model vocabulary')
    args = parser.parse_args()
    print(json.dumps(export_tokenizer(args.output)))


if __name__ == '__main__':
    main()
