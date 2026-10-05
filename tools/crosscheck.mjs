// Independent recomputation (Node, no Python) of n_claims, n_paid, q1, median, q3 per state from raw/,
// compared to data/nfip_paid_claims_by_state.json. Exit code 1 on any difference.
// Usage: node tools/crosscheck.mjs
import { createReadStream, readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const doc = JSON.parse(readFileSync(path.join(root, 'data', 'nfip_paid_claims_by_state.json'), 'utf8'));
const [y0, y1] = doc.method.window.split('-').map(Number);
const wanted = new Set(doc.records.map((r) => r.state));

const all = new Map();   // state -> count of claims
const paid = new Map();  // state -> amounts > 0
for (let y = y0; y <= y1; y++) {
  const rl = createInterface({ input: createReadStream(path.join(root, 'raw', `claims_v3_${y}.jsonl`)), crlfDelay: Infinity });
  for await (const line of rl) {
    if (!line) continue;
    const c = JSON.parse(line);
    if (!wanted.has(c.state)) continue;
    all.set(c.state, (all.get(c.state) || 0) + 1);
    const a = c.amountPaidOnBuildingClaim;
    if (typeof a === 'number' && a > 0) {
      if (!paid.has(c.state)) paid.set(c.state, []);
      paid.get(c.state).push(a);
    }
  }
}

// R type 7: h = (n-1)p, x[floor h] + (h - floor h)(x[floor h + 1] - x[floor h])
function q7(sorted, p) {
  const h = (sorted.length - 1) * p;
  const j = Math.floor(h);
  const g = h - j;
  return j + 1 < sorted.length ? sorted[j] + g * (sorted[j + 1] - sorted[j]) : sorted[j];
}

const TOL = 0.005 + 1e-9; // published values are rounded to the cent
let diffs = 0;
for (const rec of doc.records) {
  const v = (paid.get(rec.state) || []).slice().sort((a, b) => a - b);
  const mine = { n_claims: all.get(rec.state) || 0, n_paid: v.length };
  const minN = doc.method.min_n_paid;
  if (v.length >= minN) Object.assign(mine, { q1: q7(v, 0.25), median: q7(v, 0.5), q3: q7(v, 0.75) });
  else Object.assign(mine, { q1: null, median: null, q3: null });
  for (const k of Object.keys(mine)) {
    const a = mine[k], b = rec[k];
    const same = a === null || b === null ? a === b
      : (k.startsWith('n_') ? a === b : Math.abs(a - b) <= TOL);
    if (!same) { diffs++; console.log(`DIFF ${rec.state} ${k}: node=${a} json=${b}`); }
  }
}
console.log(`crosscheck: ${doc.records.length} states, ${diffs} difference(s)`);
process.exit(diffs ? 1 : 0);
