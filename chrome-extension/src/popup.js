const $ = (id) => document.getElementById(id);

let currentLedger = null;

function setStatus(msg) {
  $("status").textContent = msg;
}

async function load() {
  const resp = await chrome.runtime.sendMessage({ type: "GET_STATE" });
  if (!resp || !resp.ok) {
    setStatus("ERROR: Could not read background state.");
    return;
  }
  currentLedger = resp.ledger;
  const s = resp.stats;
  $("s-pass").textContent = s.passed;
  $("s-block").textContent = s.blocked;
  $("s-blind").textContent = s.blind;
  $("s-bypass").textContent = s.bypasses;

  $("l-dsh").value = currentLedger.lanes.dsh_web.status;
  $("l-glm").value = currentLedger.lanes.glm_zai.status;
  $("l-claude").value = currentLedger.lanes.claude_code.status;
  $("l-pennyd").value = currentLedger.lanes.pennyd_local.status;

  $("g-mode").value = currentLedger.mode;
  $("g-url").value = currentLedger.cloudVerifierUrl || "";
  $("g-strict").checked = Boolean(currentLedger.strictContractMode);
  $("g-chore").checked = Boolean(currentLedger.allowBootstrapChore);
  $("g-autoreject").checked = Boolean(currentLedger.autoRejectEnabled);
  setStatus(`Audit ledger: ${resp.auditCount} records`);
}

$("btn-save").addEventListener("click", async () => {
  const updated = structuredClone(currentLedger);
  updated.lanes.dsh_web.status = $("l-dsh").value;
  updated.lanes.glm_zai.status = $("l-glm").value;
  updated.lanes.claude_code.status = $("l-claude").value;
  updated.lanes.pennyd_local.status = $("l-pennyd").value;
  updated.mode = $("g-mode").value;
  updated.cloudVerifierUrl = $("g-url").value.trim();
  updated.strictContractMode = $("g-strict").checked;
  updated.allowBootstrapChore = $("g-chore").checked;
  updated.autoRejectEnabled = $("g-autoreject").checked;

  const resp = await chrome.runtime.sendMessage({ type: "SAVE_LEDGER", ledger: updated });
  if (resp && resp.ok) {
    currentLedger = resp.ledger;
    setStatus("SAVED: Estate ledger & gates enforced immediately.");
  } else {
    setStatus("SAVE FAILED");
  }
});

$("btn-selftest").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("selftest.html") });
});

$("btn-export").addEventListener("click", async () => {
  const resp = await chrome.runtime.sendMessage({ type: "EXPORT_AUDIT" });
  if (!resp || !resp.ok) return setStatus("EXPORT FAILED");
  const blob = new Blob([resp.jsonl], { type: "application/x-ndjson" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "meridian-web-audit.jsonl";
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  setStatus(`EXPORTED ${resp.count} audit records.`);
});

$("btn-reset").addEventListener("click", async () => {
  const resp = await chrome.runtime.sendMessage({ type: "RESET_STATS" });
  if (resp && resp.ok) {
    await load();
    setStatus("Counters reset.");
  }
});

load();
