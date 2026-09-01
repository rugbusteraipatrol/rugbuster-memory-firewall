# Judge guide

This page is the shortest path to verify the submission without trusting the
demo video.

## 90-second path

1. Read the policy branch and fail-closed branch in
   [`firewall.py`](src/rugbuster_memory_firewall/firewall.py#L219).
2. Read the fresh-session and deletion tests in
   [`test_sibyl_sdk.py`](tests/test_sibyl_sdk.py#L55).
3. Open the public Base Sepolia
   [BLOCK receipt](https://base-sepolia.blockscout.com/tx/0x13fdde4a65e27ad8dbe3843439f965eb0293dd630d0884e3b56c62eb43412eca).
4. Compare its recorded decision and memory hashes with
   [`base-sepolia-decision-receipt.json`](evidence/base-sepolia-decision-receipt.json),
   then use the console to match the recorded memory hash and policy to a fresh run.

## Five-minute path

After setup, run:

```bash
.venv/bin/python scripts/judge_check.py --live
```

On Windows:

```powershell
.venv\Scripts\python scripts\judge_check.py --live
```

The command runs all Python tests, all contract tests, the deletion gate, and
the real Avalanche verification. The real verifier:

- re-resolves each token creator from Routescan;
- re-reads public Avalanche transaction receipts and WAVAX logs;
- validates transfer direction, amount, elapsed time, and return ratio;
- writes the two verified events to a new Sibyl database;
- closes the client and opens a fresh client;
- requests a clean-current-signal decision for a different token by the same
  creator;
- expects `BLOCK_REPEAT_DEPLOYER`.

## Gate question

**Delete Sibyl Memory. Does the core product still work?**

No. `MemoryFirewall(None)` returns `MEMORY_REQUIRED`. It cannot return an
actionable verdict. Run only that proof with:

```bash
.venv/bin/python -m pytest \
  tests/test_sibyl_sdk.py::test_deleted_memory_layer_returns_memory_required -vv
```

## Partner proof

Base does actual product work, not decorative deployment. The demo decision is
written to `DecisionReceiptRegistry`, binding the off-chain policy decision to
the exact Sibyl memory-evidence hash. The contract is deployed, exercised, and
source-verified on Base Sepolia. A later fresh run produces its own timestamped
decision hash; it is linked to the receipt by the same memory-evidence hash and
policy, not misrepresented as the identical execution.

## Honest boundaries

- The real evidence proves on-chain transaction behavior, not wallet ownership
  or intent.
- The policy is deterministic; no model-generated allegation is accepted.
- Scanner labels alone cannot create verified critical evidence.
- PMF claims are limited to public RugBuster development artifacts unless a
  publicly verifiable pilot or user artifact is added before submission.
