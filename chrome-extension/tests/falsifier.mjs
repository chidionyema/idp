// Node falsifier for the membrane gate engine. Runs the same vectors as src/selftest.html,
// without a browser, so CI and the optimus measure can run it.
//   node chrome-extension/tests/falsifier.mjs
// Prints optimus.membrane.falsifier_failures=<n>; exits 0 only when n is 0 AND a stub engine
// that admits everything, and one that blocks everything, are both caught (a falsifier that cannot fail is not a falsifier).
import { DEFAULT_LEDGER, evaluateEgress } from "../src/gate-engine.js";
import { VECTORS } from "../src/vectors.js";

function failures(engine) {
  const failed = [];
  for (const v of VECTORS) {
    const res = engine(v.payload, DEFAULT_LEDGER, { host: "selftest.local" });
    const verdictOk = res.verdict === v.expectedVerdict;
    const codeOk = v.expectedCode ? res.codes.includes(v.expectedCode) : res.codes.length === 0;
    if (!(verdictOk && codeOk)) failed.push(`${v.id}: got ${res.verdict} [${res.codes.join(",")}]`);
  }
  return failed;
}

const real = failures(evaluateEgress);
const admitAll = failures(() => ({ verdict: "PASS", codes: [] }));
const blockAll = failures(() => ({ verdict: "BLOCKED", codes: ["ANY"] }));
for (const f of real) console.error(`FAIL ${f}`);
console.error(`membrane falsifier: ${VECTORS.length - real.length}/${VECTORS.length} vectors pass; admit-all stub caught on ${admitAll.length}, block-all stub caught on ${blockAll.length}`);
console.log(`optimus.membrane.falsifier_failures=${real.length}`);
if (admitAll.length === 0 || blockAll.length === 0) {
  console.error("FAIL the vectors cannot tell a gate from no gate, or from a wall");
  process.exit(1);
}
process.exit(real.length === 0 ? 0 : 1);
