const $ = (id) => document.getElementById(id);

function short(value) {
  if (!value || value.length < 18) return value;
  return `${value.slice(0, 10)}...${value.slice(-8)}`;
}

function state(stepId, label, kind = "complete") {
  const step = $(stepId);
  step.classList.remove("complete", "failed");
  step.classList.add(kind);
  step.querySelector(".step-state").textContent = label;
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(`Request failed: ${response.status}`);
  return response.json();
}

async function loadSummary() {
  const data = await request("/api/summary");
  $("case-id").textContent = data.case_id;
  $("event-count").textContent = `${data.historical_events.length} CRITICAL`;
  $("deployer").textContent = data.deployer;
  $("recall-target").textContent = data.recall_target.token_address;
  $("explorer-link").href = data.receipt.explorer_tx;
}

$("run-live").addEventListener("click", async () => {
  const button = $("run-live");
  button.disabled = true;
  button.textContent = "Verifying...";
  $("event-list").innerHTML = '<p class="muted">Querying Routescan and Avalanche RPC...</p>';
  try {
    const data = await request("/api/proof/live", { method: "POST" });
    $("event-list").innerHTML = data.observations.map((item) => `<p>${item}</p>`).join("");
    $("decision-reason").textContent = `${data.decision.verdict} / ${data.decision.reason_codes.join(", ")} / evidence ${data.decision.evidence_count}`;
    $("final-verdict").textContent = data.decision.verdict;
    state("step-evidence", "VERIFIED");
    state("step-recall", "BLOCKED");
  } catch (error) {
    $("event-list").innerHTML = '<p class="muted">Live proof failed. Check network access and retry.</p>';
    state("step-evidence", "FAILED", "failed");
  } finally {
    button.disabled = false;
    button.textContent = "Run live proof";
  }
});

$("delete-memory").addEventListener("click", async () => {
  const button = $("delete-memory");
  button.disabled = true;
  try {
    const data = await request("/api/proof/deletion", { method: "POST" });
    $("deletion-output").textContent = `${data.status.toUpperCase()} / ${data.verdict} / ${data.reason_codes.join(", ")}`;
  } catch (error) {
    $("deletion-output").textContent = "Deletion test failed to run";
  } finally {
    button.disabled = false;
  }
});

$("verify-base").addEventListener("click", async () => {
  const button = $("verify-base");
  button.disabled = true;
  button.textContent = "Checking...";
  try {
    const data = await request("/api/proof/base", { method: "POST" });
    $("receipt-status").textContent = data.status.toUpperCase();
    $("receipt-status").className = data.status === "verified" ? "clean" : "blocked";
    $("decision-reason").title = `Decision ${short(data.decoded.decision_hash)} / Memory ${short(data.decoded.memory_evidence_hash)}`;
    state("step-base", data.status.toUpperCase(), data.status === "verified" ? "complete" : "failed");
  } catch (error) {
    $("receipt-status").textContent = "CHECK FAILED";
    $("receipt-status").className = "blocked";
    state("step-base", "FAILED", "failed");
  } finally {
    button.disabled = false;
    button.textContent = "Verify";
  }
});

loadSummary().catch(() => {
  $("case-id").textContent = "Evidence unavailable";
});
