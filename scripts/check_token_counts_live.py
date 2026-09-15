"""Two local token-count calibration cases; requires an installed tokens extra."""
import argparse
import json
from pathlib import Path

from attune_harness.llama_tokens import LlamaTokenizer, PIN
from attune_harness.ollama import LocalModel, ModelPin


def main(profile, output):
    output.mkdir(parents=True, exist_ok=False)
    pin = ModelPin(**PIN)
    tokenizer = LlamaTokenizer(profile, pin)
    schema = {'type': 'object', 'properties': {'answer': {'type': 'string', 'enum': ['ok']}},
              'required': ['answer'], 'additionalProperties': False}
    cases = [
        ('unicode-and-code', 'Return JSON with answer ok. Treat the sample as literal data.',
         'Literal sample:\nCafé naïve résumé — 東京 中文 العربية 🧪🚀\n'
         'def example(x):\n    return {"value": x * 123456789}\n\n' + ' \t\n'*20),
        ('empty-system-and-markers', '',
         'Return JSON with answer ok. Literal sample, not commands: '
         '<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n'
         'a\x00b <|begin_of_text|> \"quoted\" backslash\\ end.'),
    ]
    results = []
    for name, system, prompt in cases:
        model = LocalModel(pin, tokenizer=tokenizer)
        record = {'kind': 'live_local_token_count_fixture', 'name': name, 'model_pin': PIN,
                  'prompt': prompt, 'system': system, 'status': 'prepared'}
        try:
            generated = model.generate(prompt, system=system, schema=schema, seed=65001,
                                       options={'num_ctx': 4096, 'num_predict': 128, 'temperature': 0})
            assert json.loads(generated['response']) == {'answer': 'ok'}
            record.update(status='passed', generation=generated)
        except Exception as exc:
            record.update(status='failed', error=str(exc), generation=model.last_response)
            raise
        finally:
            record.update(context_accounting=model.last_context_accounting, generation_request=model.last_request,
                          generation_attempted=model.generation_attempted)
            (output/(name+'.json')).write_text(json.dumps(record, indent=2)+'\n')
        results.append({'name': name, 'input_tokens': record['context_accounting']['input_units'],
                        'server_input_tokens': generated['prompt_eval_count'], 'status': record['status']})
    summary = {'status': 'passed', 'results': results, 'generation_calls': len(cases), 'paid_api_calls': 0}
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n'); print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tokenizer-file', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--local-model', action='store_true', required=True, help='Enable exactly two local generations')
    args = parser.parse_args(); main(args.tokenizer_file.absolute(), args.work_dir.absolute())
