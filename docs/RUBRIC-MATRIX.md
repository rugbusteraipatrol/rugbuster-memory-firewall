# Rubric evidence matrix

## Gate: memory is load-bearing

| Judge check | Evidence |
| --- | --- |
| Fresh session recalls earlier state | `test_fresh_session_recall_changes_decision` and `scripts/verify_real_case.py` |
| Memory calls are on the critical path | `MemoryFirewall.pre_sign()` reads memory before every actionable verdict |
| Deletion breaks the claimed function | `test_deleted_memory_layer_returns_memory_required` |
| Judge can find the calls quickly | README links directly to the write, read, policy, and failure branches |

## Memory is load-bearing - 40 points

- WARM entity coordinates decisions across sessions and across tokens from the
  same deployer.
- COLD events preserve the observation and decision sequence.
- HOT state tracks the current analysis and final decision hash.
- REFERENCE state binds the policy thresholds and version.
- History does not merely appear in a response: it changes `ALLOW` to `BLOCK`.

## Innovation and originality - 25 points

The product applies persistent agent memory as a deterministic pre-sign safety
control. A stateless scan asks only whether a token looks risky now. This agent
also asks whether the independently resolved deployer has verified history that
should change the proposed action.

No "first" claim is made without a documented competitive review.

## Technical execution - 20 points

- 23 Python tests cover memory behavior, API behavior, resolver validation,
  isolation, deduplication, and fail-closed states.
- 4 Solidity tests cover receipt immutability and invalid inputs.
- Real evidence is machine-readable and independently re-queried.
- The contract is deployed, exercised, and source-verified.
- GitHub Actions reproduces the deterministic suite on every push.

## Pitch and presentation - 15 points

The demo is one story: clean current token, known deployer, fresh-session recall,
changed decision, deletion failure, Base receipt. The required recall segment is
continuous and includes an on-screen UTC timestamp and commit hash.

## PMF bonus - up to 10 points

Public prior work proves sustained development for the named audience of token
users, wallets, bots, and launch workflows. It does not by itself prove a pilot
or usage. Do not claim a nonzero PMF bonus unless a judge can verify an actual
pilot, user, waitlist, or usage artifact in five minutes.

## Base multiplier

The demo exercises a real `recordDecision` call. The public receipt stores the
decision hash and Sibyl memory-evidence hash and is visible on Base Sepolia.
