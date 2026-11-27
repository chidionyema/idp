import { DEFAULT_LEDGER, evaluateEgress } from "./gate-engine.js";
import { VECTORS } from "./vectors.js";


async function run() {
  const tbody = document.getElementById("rows");
  let passedVectors = 0;

  for (const v of VECTORS) {
    const res = evaluateEgress(v.payload, DEFAULT_LEDGER, { host: "selftest.local" });
    const verdictOk = res.verdict === v.expectedVerdict;
    const codeOk = v.expectedCode ? res.codes.includes(v.expectedCode) : res.codes.length === 0;
    const ok = verdictOk && codeOk;
    if (ok) passedVectors += 1;

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><code>${v.id}</code></td>
      <td>${v.desc}</td>
      <td>${v.expectedVerdict}${v.expectedCode ? "<br><code>" + v.expectedCode + "</code>" : ""}</td>
      <td><b>${res.verdict}</b><br><code>${res.codes.join(", ") || `NONE (${res.passedCount}/${res.totalChecks} PASS)`}</code></td>
      <td class="${ok ? "ok" : "fail"}">${ok ? "VERIFIED" : "FAILED"}</td>
    `;
    tbody.appendChild(tr);
  }

  const summary = document.getElementById("summary");
  const bytes = new TextEncoder().encode(`MERIDIAN_SELFTEST:${passedVectors}/${VECTORS.length}`);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const hash = Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 16);

  summary.textContent = `ADVERSARIAL FALSIFIER RESULT: ${passedVectors}/${VECTORS.length} VECTORS PASSED | RECEIPT: ${hash} | ENGINE: V8 NATIVE`;
  summary.style.borderColor = passedVectors === VECTORS.length ? "#16a34a" : "#dc2626";
  summary.style.color = passedVectors === VECTORS.length ? "#4ade80" : "#f87171";
}

run();
