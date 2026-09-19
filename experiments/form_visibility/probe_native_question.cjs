// Read-only, version-specific probe of installed Codex question handlers.
// Synthetic React elements/state only: no app connection, browser or real answer.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');

const archive = '/Applications/ChatGPT.app/Contents/Resources/app.asar';
const fd = fs.openSync(archive, 'r');
const prefix = Buffer.alloc(16);
fs.readSync(fd, prefix, 0, 16, 0);
const headerBytes = Buffer.alloc(prefix.readUInt32LE(12));
fs.readSync(fd, headerBytes, 0, headerBytes.length, 16);
const header = JSON.parse(headerBytes.toString());
const base = 8 + prefix.readUInt32LE(4);
const sources = {};
function member(path) {
  let item = header;
  for (const part of path.split('/')) item = item.files[part];
  assert(!item.unpacked);
  const bytes = Buffer.alloc(item.size);
  fs.readSync(fd, bytes, 0, bytes.length, base + Number(item.offset));
  sources[path] = crypto.createHash('sha256').update(bytes).digest('hex');
  return bytes.toString();
}
const primary = member('webview/assets/app-primary-4af6ed7f68d1.js');
const initial = member('webview/assets/app-initial-4d7ea7f81c2d.js');
fs.closeSync(fd);
function extract(source, name) {
  const start = source.indexOf(`function ${name}(`);
  assert(start >= 0, `Installed bundle changed: ${name} missing`);
  const ends = ['}function ', '}var '].map(s => source.indexOf(s, start)).filter(n => n >= 0);
  assert(ends.length);
  return source.slice(start, Math.min(...ends) + 1);
}
const functions = ['dZo', 'hZo', 'mZo', 'gZo', 'v8'].map(n => extract(initial, n));
functions.push(extract(primary, 'W1n'), extract(primary, 'F1n'));
const element = (type, props) => ({type, props});
const ctx = {
  G1n: {c: n => Array(n).fill(Symbol.for('react.memo_cache_sentinel'))},
  L1n: {c: n => Array(n).fill(Symbol.for('react.memo_cache_sentinel'))},
  E3: {jsx: element, jsxs: element}, S3: {jsx: element},
  Ft: {div: 'animated-div'}, T3: {}, K1n: '(Recommended)',
  Mw: 'badge', Z: 'text', x3: 'marker', nw: 'icon', FJe: 'arrow', cYe: 'arrow',
  $: (...values) => values.filter(Boolean).join(' '),
  I1n: highlighted => highlighted ? 'highlighted' : 'normal',
  sp: (_scope, callback) => callback(),
};
for (const name of ['S8', 'b8', 'x8', 'w8', 'C8', 'T8']) ctx[name] = name;
vm.createContext(ctx);
vm.runInContext(functions.join('\n'), ctx, {timeout: 1000});
const rows = new Map();
const keyOf = (atom, key) => atom + ':' + JSON.stringify(key);
const scope = {
  get(atom, key) {
    if (atom === 'w8' || atom === 'T8') {
      const panel = this.get('C8', key.hostId).get(key.threadId) ?? null;
      return atom === 'T8' ? panel?.selectedQuestionKey ?? null : panel;
    }
    return rows.get(keyOf(atom, key)) ?? (atom === 'C8' ? new Map() : atom === 'b8' ? [] : null);
  },
  set(atom, key, value) {
    rows.set(keyOf(atom, key), typeof value === 'function' ? value(this.get(atom, key)) : value);
  },
};
const thread = {hostId: 'synthetic-host', threadId: 'synthetic-thread'};
const turn = {...thread, entityKey: 'synthetic-turn'};
const question = {...turn, itemId: 'synthetic-question'};
const now = 1000;
function open() {
  rows.clear();
  ctx.dZo(scope, turn, [{id: question.itemId}], 'synthetic-turn-id', now, false);
}
const checks = [];
function check(name, work) { work(); checks.push({name, result: 'passed'}); }
let hovered, selected;
const tree = ctx.W1n({
  hasComposerAppearance: true, options: [{id: '0', value: 'Synthetic A'}],
  selectedOptionId: null, onHover: id => { hovered = id; },
  onSelect: id => { selected = id; },
});
const row = tree.props.children[0].props.children;
const button = ctx.F1n(row.props);
check('pointer-enter updates hover without selecting an answer', () => {
  button.props.onPointerEnter();
  assert.equal(hovered, '0'); assert.equal(selected, undefined);
  assert.equal(button.props['aria-checked'], false);
});
check('explicit click selects the option (positive control)', () => {
  button.props.onClick(); assert.equal(selected, '0');
});
check('automatic question opening assigns a 30-second deadline', () => {
  open(); assert.equal(scope.get('S8', question).deadlineMs, now + 30000);
});
check('hover does not clear the deadline; matching timeout closes the panel', () => {
  open(); button.props.onPointerEnter();
  assert.equal(scope.get('S8', question).deadlineMs, now + 30000);
  ctx.gZo(scope, question, now + 30000);
  assert.equal(scope.get('w8', thread), null);
  assert.equal(scope.get('S8', question).lastSubmission, null);
});
check('user-interaction handler clears deadline and stale timeout cannot close', () => {
  open(); ctx.hZo(scope, question);
  assert.equal(scope.get('S8', question).deadlineMs, null);
  ctx.gZo(scope, question, now + 30000);
  assert.notEqual(scope.get('w8', thread), null);
});
check('editing the draft clears the deadline', () => {
  open(); ctx.mZo(scope, question, 'Synthetic draft');
  assert.equal(scope.get('S8', question).deadlineMs, null);
  assert.equal(scope.get('S8', question).draft, 'Synthetic draft');
});
const staticChecks = [
  ['native panel hides after turn leaves inProgress', 'y!==`inProgress`||C?.type!==`agentMessage`'],
  ['timer invokes timeout dismissal', 'window.setTimeout(()=>{Wfe(c,s,`timeout`,T)}'],
  ['pointer-down capture calls user-interaction callback', 'onPointerDownCapture:pt'],
];
for (const [name, token] of staticChecks) {
  assert(primary.includes(token)); staticChecks[staticChecks.findIndex(x => x[0] === name)] = {name, result: 'present'};
}
open();
// Protection-removal control: omit hZo, then replay the deadline callback.
ctx.gZo(scope, question, now + 30000);
assert.equal(scope.get('w8', thread), null);
console.log(JSON.stringify({
  mode: 'actual extracted UI handlers; synthetic elements/state; no real UI interaction',
  archive, sources, checks, static_checks: staticChecks,
  guard_removal: {removed: 'user interaction clearing the deadline', detected: true},
  limitations: ['No visible-host incident reproduction', 'No real pointer event stream or screenshot',
    'No proof which event caused Patrick’s incident', 'No app patch or real answer submission'],
}, null, 2));
