"""Seeded defects in complete current modules; reference bytes never reach workers."""

import ast
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def case(name, module, symbol, changes, behavior, checks):
    path = ROOT / "src/attune_harness" / (module + ".py")
    correct = path.read_text()
    target = next(n for n in ast.parse(correct).body if isinstance(n, ast.FunctionDef) and n.name == symbol)
    lines = correct.splitlines(True)
    body = "".join(lines[target.lineno - 1:target.end_lineno])
    broken_body = body
    for old, new in changes:
        assert broken_body.count(old) == 1, (name, old)
        broken_body = broken_body.replace(old, new)
    broken = "".join(lines[:target.lineno - 1]) + broken_body + "".join(lines[target.end_lineno:])
    assert broken != correct and len(checks) == 6
    ast.parse(broken)
    return {"id": name, "module": module, "symbol": symbol, "correct": correct, "broken": broken,
            "behavior": behavior, "checks": checks, "seed_count": len(changes),
            "origin": str(path.relative_to(ROOT)), "origin_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def cases():
    return [
        case("markdown-escape", "documentation", "_escape",
             [("('\\\\', '`'", "('`'")],
             "Escape Markdown metacharacters including existing backslashes exactly once per original character. Preserve Unicode and plain text.", [
                 "self.assertEqual(subject._escape('a' + chr(92) + 'b'), 'a' + chr(92) * 2 + 'b')",
                 "self.assertEqual(subject._escape('*x*'), chr(92)+'*x'+chr(92)+'*')",
                 "self.assertEqual(subject._escape('naïve text'), 'naïve text')",
                 "self.assertEqual(subject._escape('[a]'), chr(92)+'[a'+chr(92)+']')",
                 "self.assertEqual(subject._escape(chr(92)*2), chr(92)*4)",
                 "self.assertEqual(subject._escape(''), '')",
             ]),
        case("public-symbols", "documentation", "_symbols",
             [("ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef", "ast.FunctionDef, ast.ClassDef"),
              ("if node.name in result:", "if False:")],
             "Inventory public top-level synchronous/async functions and classes, excluding private and nested declarations. Preserve line spans and signatures, and reject duplicate public names.", [
                 "s=subject.Source('x.py','async def fetch(x):\\n    return x\\n','x'); self.assertEqual(subject._symbols(s)['fetch'], (1,2,'async def fetch(x)'))",
                 "s=subject.Source('x.py','def a():\\n    pass\\ndef a():\\n    pass\\n','x'); self.assertRaises(ValueError, subject._symbols, s)",
                 "s=subject.Source('x.py','def _hidden():\\n    pass\\nclass Public:\\n    pass\\n','x'); self.assertEqual(subject._symbols(s), {'Public':(3,4,None)})",
                 "s=subject.Source('x.py','def outer():\\n    def inner():\\n        pass\\n','x'); self.assertEqual(list(subject._symbols(s)), ['outer'])",
                 "s=subject.Source('x.py','async def one(x: int) -> str:\\n    pass\\n','x'); self.assertEqual(subject._symbols(s)['one'][2], 'async def one(x: int) -> str')",
                 "s=subject.Source('x.py','class A:\\n    pass\\ndef A():\\n    pass\\n','x'); self.assertRaises(ValueError, subject._symbols, s)",
             ]),
        case("skills-token-bounds", "native", "validate_skills_context_tokens",
             [("type(value) is not int", "not isinstance(value, int)"), ("1 <= value <= 10_000", "1 <= value <= 1_000")],
             "Accept only actual integers from 1 through 10000 inclusive, rejecting bool, floats and out-of-range values; return the original accepted integer.", [
                 "self.assertEqual(subject.validate_skills_context_tokens(10000), 10000)",
                 "self.assertRaises(ValueError, subject.validate_skills_context_tokens, True)",
                 "self.assertEqual(subject.validate_skills_context_tokens(1), 1)",
                 "self.assertRaises(ValueError, subject.validate_skills_context_tokens, 0)",
                 "self.assertEqual(subject.validate_skills_context_tokens(7500), 7500)",
                 "[self.assertRaises(ValueError, subject.validate_skills_context_tokens, x) for x in (False, 10001, 1.0, '1')]",
             ]),
        case("nonnegative-count", "operations", "count",
             [("type(value) is not int", "not isinstance(value, int)"), ("value < 0", "value <= 0")],
             "Accept integer counts including zero, reject bool/non-integers/negative counts, return the value, and retain the caller's name in validation errors.", [
                 "self.assertEqual(subject.count(0, 'calls'), 0)",
                 "self.assertRaises(ValueError, subject.count, True, 'calls')",
                 "self.assertEqual(subject.count(100, 'calls'), 100)",
                 "self.assertRaisesRegex(ValueError, 'calls', subject.count, -1, 'calls')",
                 "self.assertEqual(subject.count(0, 'tokens'), 0)",
                 "[self.assertRaises(ValueError, subject.count, x, 'tokens') for x in (True, False, 2.0, '2', None)]",
             ]),
        case("finite-amount", "operations", "amount",
             [(" or not math.isfinite(value)", "")],
             "Accept None or nonnegative finite int/float amounts and preserve None; reject bool, NaN, infinities, negatives and other types.", [
                 "self.assertRaises(ValueError, subject.amount, float('inf'), 'cost')",
                 "self.assertRaises(ValueError, subject.amount, float('nan'), 'cost')",
                 "self.assertIsNone(subject.amount(None, 'cost'))",
                 "self.assertEqual(subject.amount(1.25, 'cost'), 1.25)",
                 "[self.assertRaises(ValueError, subject.amount, x, 'cost') for x in (float('-inf'), float('nan'), True, -1, '2')]",
                 "self.assertEqual(subject.amount(0, 'cost'), 0)",
             ]),
        case("context-output-reserve", "ollama", "validate_output_budget",
             [("num_predict >= num_ctx - 512", "num_predict > num_ctx - 512")],
             "Require positive integer budgets, context 1024..16384, and output strictly below context minus 512; reject equality as well as excess output and bool inputs.", [
                 "self.assertRaises(ValueError, subject.validate_output_budget, 1024, 512)",
                 "self.assertIsNone(subject.validate_output_budget(1024,511))",
                 "self.assertRaises(ValueError, subject.validate_output_budget, 1023, 1)",
                 "self.assertIsNone(subject.validate_output_budget(16384, 15871))",
                 "self.assertRaises(ValueError, subject.validate_output_budget, 4096, 3584)",
                 "[self.assertRaises(ValueError, subject.validate_output_budget, *x) for x in ((True,1),(2048,True),(16385,1),(1024,0))]",
             ]),
        case("json-bytes-and-duplicates", "review_contract", "parse_json",
             [("len(raw.encode('utf-8'))", "len(raw)"), ("object_pairs_hook=_unique_object, ", "")],
             "Enforce JSON input limits in UTF-8 bytes; reject duplicate object keys at every nesting level and non-finite constants while accepting valid JSON within the exact limit.", [
                 "self.assertRaises(ValueError, subject.parse_json, '\"é\"', 3)",
                 "self.assertRaises(ValueError, subject.parse_json, '{\"x\":1,\"x\":2}')",
                 "self.assertEqual(subject.parse_json('\"é\"',4), 'é')",
                 "self.assertRaises(ValueError, subject.parse_json, '[NaN]')",
                 "self.assertRaises(ValueError, subject.parse_json, '{\"a\":{\"b\":1,\"b\":2}}')",
                 "self.assertRaises(ValueError, subject.parse_json, '\"😀\"', 5)",
             ]),
        case("exact-fields", "review_contract", "fields",
             [("set(value) != expected", "not expected.issubset(value)")],
             "Require a dictionary containing exactly the expected field names; reject extra fields, missing fields and non-dictionaries while allowing any field values.", [
                 "self.assertRaises(ValueError, subject.fields, {'a':1,'extra':2}, ['a'])",
                 "self.assertIsNone(subject.fields({'a':None}, ['a']))",
                 "self.assertRaises(ValueError, subject.fields, {}, ['a'])",
                 "self.assertRaises(ValueError, subject.fields, ['a'], ['a'])",
                 "self.assertRaises(ValueError, subject.fields, {'unexpected':False}, [])",
                 "self.assertIsNone(subject.fields({'b':False,'a':0}, ['a','b']))",
             ]),
        case("bounded-text-preservation", "review_contract", "bounded_text",
             [("len(value.encode('utf-8'))", "len(value)"), ("return value", "return value.strip()")],
             "Validate nonblank text against a UTF-8 byte limit, but return the exact original string including leading/trailing whitespace. Reject other types and all-whitespace text.", [
                 "self.assertRaises(ValueError, subject.bounded_text, 'éé', 'label', 3)",
                 "self.assertEqual(subject.bounded_text(' x ', 'label', 3), ' x ')",
                 "self.assertEqual(subject.bounded_text('é', 'label', 2), 'é')",
                 "self.assertRaises(ValueError, subject.bounded_text, '  ', 'label', 9)",
                 "self.assertEqual(subject.bounded_text('\\ttext\\n', 'label', 9), '\\ttext\\n')",
                 "self.assertRaises(ValueError, subject.bounded_text, '😀', 'label', 3)",
             ]),
        case("identifier-full-match", "voyage_sources", "identifier",
             [("re.fullmatch(", "re.match(")],
             "Identifiers must consist entirely of 1..64 ASCII letters, digits, underscores or hyphens; reject trailing punctuation/newlines and oversize values while preserving accepted text.", [
                 "self.assertRaises(ValueError, subject.identifier, 'valid.bad')",
                 "self.assertRaises(ValueError, subject.identifier, 'a'*65)",
                 "self.assertEqual(subject.identifier('Repo_2-x'), 'Repo_2-x')",
                 "self.assertRaises(ValueError, subject.identifier, '')",
                 "self.assertRaises(ValueError, subject.identifier, 'repo\\n')",
                 "self.assertEqual(subject.identifier('a'*64), 'a'*64)",
             ]),
        case("recursive-root-glob", "voyage_sources", "matches",
             [(" or (p.startswith('**/') and fnmatch.fnmatchcase(path, p[3:]))", "")],
             "A **/ glob must also match its root-level form; preserve ordinary fnmatchcase behavior, case sensitivity, multiple patterns and empty-pattern results.", [
                 "self.assertTrue(subject.matches('main.py',['**/*.py']))",
                 "self.assertTrue(subject.matches('lib/main.py',['**/*.py']))",
                 "self.assertFalse(subject.matches('main.txt',['**/*.py']))",
                 "self.assertFalse(subject.matches('main.py',[]))",
                 "self.assertTrue(subject.matches('README.md',['unused','**/README.md']))",
                 "self.assertFalse(subject.matches('MAIN.PY',['**/*.py']))",
             ]),
        case("scoped-exclusion", "voyage_sources", "in_scope",
             [(" and\n", " or\n")],
             "Require repository membership and absence of the exact repo/path exclusion pair. Excluding a path in another repository must not exclude this passage; do not mutate the scope.", [
                 "self.assertFalse(subject.in_scope({'repo_id':'a','path':'x'}, {'repo_ids':['a'],'exclude_paths':[{'repo_id':'a','path':'x'}]}))",
                 "self.assertFalse(subject.in_scope({'repo_id':'b','path':'x'}, {'repo_ids':['a'],'exclude_paths':[]}))",
                 "self.assertTrue(subject.in_scope({'repo_id':'a','path':'x'}, {'repo_ids':['a'],'exclude_paths':[{'repo_id':'b','path':'x'}]}))",
                 "self.assertTrue(subject.in_scope({'repo_id':'a','path':'y'}, {'repo_ids':['a'],'exclude_paths':[{'repo_id':'a','path':'x'}]}))",
                 "self.assertFalse(subject.in_scope({'repo_id':'outside','path':'y'}, {'repo_ids':[],'exclude_paths':[]}))",
                 "s={'repo_ids':['a'],'exclude_paths':[{'repo_id':'a','path':'x'}]}; old=copy.deepcopy(s); self.assertFalse(subject.in_scope({'repo_id':'a','path':'x'},s)); self.assertEqual(s,old)",
             ]),
        case("sql-literal-escaping", "voyage_retrieval", "predicate",
             [("s.replace(\"'\", \"''\")", "s")],
             "Build the same repository/exclusion predicate while SQL-escaping every single quote in repository IDs and excluded paths by doubling it. Preserve all exclusion pairs and input values.", [
                 "self.assertEqual(subject.predicate({'repo_ids':[\"o'reilly\"],'exclude_paths':[]}), \"repo_id IN ('o''reilly')\")",
                 "s={'repo_ids':['a'],'exclude_paths':[{'repo_id':'a','path':\"x'y\"}]}; self.assertIn(\"path = 'x''y'\", subject.predicate(s))",
                 "self.assertEqual(subject.predicate({'repo_ids':['a','b'],'exclude_paths':[]}), \"repo_id IN ('a','b')\")",
                 "s={'repo_ids':['a'],'exclude_paths':[]}; old=copy.deepcopy(s); subject.predicate(s); self.assertEqual(s,old)",
                 "s={'repo_ids':['a'],'exclude_paths':[{'repo_id':\"b'c\",'path':'x'}]}; self.assertIn(\"repo_id = 'b''c'\",subject.predicate(s))",
                 "s={'repo_ids':[\"a'b'c\"],'exclude_paths':[]}; self.assertEqual(subject.predicate(s),\"repo_id IN ('a''b''c')\")",
             ]),
        case("rank-fusion", "voyage_retrieval", "fuse",
             [("dict.fromkeys(rows)", "rows"), ("(-scores[key], key)", "(-scores[key],)")],
             "Reciprocal-rank fusion must count each key once per input ranking, rank first distinct occurrence from one, sum 1/(60+rank) across rankings, break equal scores by key and leave inputs unchanged.", [
                 "order,scores=subject.fuse(['a','a','b']); self.assertEqual(order,['a','b']); self.assertAlmostEqual(scores['a'],1/61); self.assertAlmostEqual(scores['b'],1/62)",
                 "self.assertEqual(subject.fuse(['z'],['a'])[0],['a','z'])",
                 "self.assertEqual(subject.fuse(),([],{}))",
                 "rows=['b','a']; old=list(rows); subject.fuse(rows); self.assertEqual(rows,old)",
                 "order,scores=subject.fuse(['b','b','a'],['a']); self.assertEqual(order,['a','b']); self.assertAlmostEqual(scores['b'],1/61); self.assertAlmostEqual(scores['a'],1/62+1/61)",
                 "self.assertEqual(subject.fuse(['y'],['x'])[0],['x','y'])",
             ]),
        case("provider-token-usage", "voyage_provider", "usage",
             [("type(tokens) is not int", "not isinstance(tokens, int)")],
             "Return None for missing/None total_tokens or a nonnegative actual integer including zero. Reject bool, float, string and negative usage without mutating provider data.", [
                 "self.assertRaises(ValueError, subject.usage, {'total_tokens':True})",
                 "self.assertIsNone(subject.usage({}))",
                 "self.assertEqual(subject.usage({'total_tokens':0}),0)",
                 "self.assertRaises(ValueError,subject.usage,{'total_tokens':-1})",
                 "self.assertRaises(ValueError, subject.usage, {'total_tokens':False})",
                 "v={'total_tokens':23}; self.assertEqual(subject.usage(v),23); self.assertEqual(v,{'total_tokens':23}); self.assertIsNone(subject.usage({'total_tokens':None}))",
             ]),
        case("module-name-boundaries", "test_scope", "module_name",
             [("path.removeprefix(\"src/\").removesuffix(\".py\")", "path.replace(\"src/\", \"\").replace(\".py\", \"\")")],
             "Derive the module hint by removing only one leading src/ and one terminal .py, replacing path separators with dots, then removing a terminal .__init__. Preserve matching text inside the path.", [
                 "self.assertEqual(subject.module_name('src/pkg/src/mod.py'), 'pkg.src.mod')",
                 "self.assertEqual(subject.module_name('src/pkg.pytools/mod.py'), 'pkg.pytools.mod')",
                 "self.assertEqual(subject.module_name('src/pkg/__init__.py'),'pkg')",
                 "self.assertEqual(subject.module_name('tests/test_a.py'),'tests.test_a')",
                 "self.assertEqual(subject.module_name('src/src/mod.py'),'src.mod')",
                 "self.assertEqual(subject.module_name('pkg/__init__helper.py'),'pkg.__init__helper')",
             ]),
        case("portable-path-vcs", "test_scope", "relative_path",
             [("(\".\", \"..\", \".git\", \".hg\", \".svn\")", "(\".\", \"..\")")],
             "Validate canonical portable relative paths and reject any .git/.hg/.svn component at any depth, traversal, empty/redundant components, absolute paths, leading options, backslashes and NULs. Preserve accepted paths.", [
                 "self.assertRaises(ValueError,subject.relative_path,'.git/config')",
                 "self.assertRaises(ValueError,subject.relative_path,'pkg/.hg/store')",
                 "self.assertEqual(subject.relative_path('src/pkg/a.py'),'src/pkg/a.py')",
                 "[self.assertRaises(ValueError,subject.relative_path,p) for p in ('../a','a//b','/a','-q','a/./b')]",
                 "self.assertRaises(ValueError,subject.relative_path,'a/.svn/entries')",
                 "self.assertEqual(subject.relative_path('docs/.github/workflow.yml'),'docs/.github/workflow.yml')",
             ]),
        case("observed-test-classification", "test_execution", "classify",
             [("if observed[\"collect_only\"]:", "if False:"),
              ("if result.returncode == 5 or observed[\"passed\"] == 0 or not observed[\"collected\"]:", "if result.returncode == 5:")],
             "Classify collected-only checks as blocked and zero-passing/zero-collected runs as no_tests. Preserve interrupted, environment-blocked, failed-assertion and genuinely passed outcomes, existing reason messages and evidence consistency checks.", [
                 "r,o=observed_case(collect_only=True); self.assertEqual(subject.classify(r,o)[0],'blocked')",
                 "r,o=observed_case(passed=0,collected=2); self.assertEqual(subject.classify(r,o)[0],'no_tests')",
                 "r,o=observed_case(); self.assertEqual(subject.classify(r,o)[0],'passed')",
                 "r,o=observed_case(failed=1,passed=0,exit_code=1); r.returncode=1; self.assertEqual(subject.classify(r,o)[0],'failed')",
                 "r,o=observed_case(passed=0,collected=0); self.assertEqual(subject.classify(r,o)[0],'no_tests'); r,o=observed_case(collect_only=True); self.assertEqual(subject.classify(r,o)[0],'blocked')",
                 "r,o=observed_case(); r.failure='timeout_effects_unknown'; self.assertEqual(subject.classify(r,o),('interrupted','timeout_effects_unknown')); r,o=observed_case(setup_errors=1); self.assertEqual(subject.classify(r,o)[0],'blocked')",
             ]),
        case("substantive-prose", "grounded_review", "text",
             [(" or value.rstrip().endswith(':')", "")],
             "Always require nonblank text. With prose=True, also reject punctuation-only text and an unfinished introduction ending in a colon after trailing whitespace; retain accepted text exactly. Plain-text mode may contain colons.", [
                 "self.assertRaises(ValueError,subject.text,'Details:','account',prose=True)",
                 "self.assertRaises(ValueError,subject.text,'!!!','account',prose=True)",
                 "self.assertEqual(subject.text('Details:','label'),'Details:')",
                 "self.assertEqual(subject.text(' Complete account. ', 'account', prose=True),' Complete account. ')",
                 "self.assertRaises(ValueError,subject.text,'Explanation:  \\n','account',prose=True)",
                 "self.assertRaises(ValueError,subject.text,'  ','label'); self.assertEqual(subject.text('Résumé 2.','account',prose=True),'Résumé 2.')",
             ]),
        case("unicode-paragraph-offsets", "passage_review", "_blocks",
             [("offset += len(block)", "offset += len(block.encode('utf-8'))")],
             "Yield exact nonblank paragraph slices with start/end offsets measured in Unicode code points, preserving text and CRLF/blank separators. Skip punctuation-only blocks without losing their offsets.", [
                 "s='éclair\\n\\nsecond'; self.assertEqual(list(subject._blocks(s)),[(0,6,'éclair'),(8,14,'second')])",
                 "s='😀 alpha\\n\\nbeta'; rows=list(subject._blocks(s)); self.assertEqual(rows[1],(9,13,'beta'))",
                 "self.assertEqual(list(subject._blocks('  alpha  ')),[(2,7,'alpha')])",
                 "self.assertEqual(list(subject._blocks('!!!\\n\\nnext')),[(5,9,'next')])",
                 "s='naïve\\r\\n\\r\\n  fin'; rows=list(subject._blocks(s)); self.assertEqual(rows,[(0,5,'naïve'),(11,14,'fin')])",
                 "self.assertEqual(list(subject._blocks('')),[]); s='é\\n\\nx'; self.assertTrue(all(s[a:b]==t for a,b,t in subject._blocks(s)))",
             ]),
    ]
