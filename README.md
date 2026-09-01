# RugBuster Memory Firewall

Built and tested with `sibyl-memory-client==0.8.0` (Lucid). See the upstream
[0.8.0 release notes](https://github.com/Sibyl-Labs/Sibyl-Memory/blob/main/docs/release-0.8.0-notes.md).

An agent pre-sign gate that remembers verified deployer history across sessions.
Before a wallet, bot, or launch workflow acts on a token, it checks Sibyl Memory
for evidence linked to the deployer. Verified critical history blocks the
action; repeated warnings require human review.

## Why Sibyl Memory is load-bearing

`MemoryFirewall.pre_sign()` makes a `MemoryClient.get_entity()` call on every
decision. A fresh session must recall a persisted deployer profile before it can
return a verdict. If memory cannot be read, the decision is
`MEMORY_REQUIRED` and the action must not continue. Removing the memory read
removes the product's ability to identify repeat deployers.

The automated test records a fixture observation, closes the first client,
opens a fresh client, and proves that persisted history changes the verdict.
The final submission demo will use independently verifiable real evidence.

### Critical path

- `src/rugbuster_memory_firewall/resolver.py` verifies the token's deployer.
- `src/rugbuster_memory_firewall/api.py` rejects unresolved or mismatched identity.
- `src/rugbuster_memory_firewall/firewall.py` reads Sibyl Memory before every verdict.
- `tests/test_sibyl_sdk.py` contains the deletion and fresh-session tests.
- `tests/test_api.py` proves the HTTP endpoint fails closed.

## Prior work

This project builds on earlier RugBuster research and collectors. Before this
hackathon, RugBuster already had AVAX and Solana token-risk records, creator
resolution logic, and a read-only feasibility audit of repeated creator
clusters. The Sibyl memory integration, load-bearing policy gate, pre-sign API,
Base Sepolia receipt contract, and hackathon demo are new work for this event.

Existing risk labels are scanner outputs, not proof that a wallet or person
committed fraud. A blocking decision requires separately verified critical
evidence with explicit provenance.

## Preparation setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\verify_sibyl.py
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python scripts\demo_fresh_session.py
.\.venv\Scripts\python scripts\live_resolver_check.py
```

The verification script uses a temporary database and does not modify the
user's real `~/.sibyl-memory/memory.db`. `demo_fresh_session.py` is explicitly a
synthetic developer smoke test, not submission evidence. It uses
`demo-memory.db` by default; pass `--db <path>` to choose another location.

## Reproduce the real AVAX case

The submission evidence is stored in
`evidence/avax-repeat-deployer-case.json`. It names every contract, pool,
creation transaction, WAVAX transfer, amount, and timestamp used by the demo.
The verifier does not trust the stored conclusion: it re-queries Routescan and
the public Avalanche RPC, validates successful receipts, confirms that the
creator is an externally owned account, and checks the transfer directions,
amounts, return ratio, and elapsed time.

```powershell
.\.venv\Scripts\python scripts\verify_real_case.py
```

After live verification, the script writes the two historical observations to
a temporary Sibyl database, closes that client, opens a fresh client, and asks
for a clean-current-signal decision on a different token from the same creator.
The expected result is `BLOCK` with `BLOCK_REPEAT_DEPLOYER`. Token names in the
artifact are display hints only and are deliberately marked unverified; policy
decisions use addresses and public transaction evidence.

## Run the pre-sign API

```powershell
$env:RUGBUSTER_MEMORY_DB = ".\runtime-memory.db"
.\.venv\Scripts\python -m uvicorn rugbuster_memory_firewall.api:create_app --factory --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/docs` for the interactive API. `POST /v1/pre-sign`
requires a supported chain, token address, current RugBuster risk, action, and
session ID. A caller-supplied deployer is optional, but when present it must
match the independently resolved address.

AVAX resolution uses Routescan's contract-creation endpoint. Solana resolution
uses the top-level creator from a RugCheck full report. The API fails closed
when either provider cannot return a validated creator. Set `ROUTESCAN_API_KEY`
only if a higher Routescan rate limit is needed; the free endpoint is keyless.

The policy binds each decision to the requested token and a canonical hash of
the proposed action. Resolver evidence, recalled history, reason codes, memory
evidence hash, decision hash, and the optional Base transaction URL are returned
in the response.

## Base Sepolia decision receipts

`DecisionReceiptRegistry.sol` provides the executed onchain action for the Base
partner track. It stores the decision hash, Sibyl memory-evidence hash, exact
`ALLOW`/`WARN`/`BLOCK` verdict, block timestamp, submitter, and readable policy
version. A decision hash can be recorded once and can never be overwritten.

```powershell
npm install
npm run base:compile
npm run base:test
npx hardhat keystore set BASE_SEPOLIA_PRIVATE_KEY
npm run base:deploy
```

The keystore command encrypts the signing key outside tracked source files. The
deployer needs a small amount of Base Sepolia ETH. After deployment, set the
public contract address as `BASE_RECEIPT_REGISTRY`, then provide `DECISION_HASH`,
`MEMORY_EVIDENCE_HASH`, `VERDICT`, and `POLICY_VERSION` before running
`npm run base:record`. The recorder refuses any network except Base Sepolia
chain ID `84532` and prints the public explorer URL after the transaction mines.

The registry is deployed and source-verified on Base Sepolia:

- Contract: `0x5F30276B3A5079E088Ec3072884286de5a868355`
- [Deployment transaction](https://base-sepolia.blockscout.com/tx/0x6b6e8115983575525143661c5e3e488e5f8b0e023b6a69e06ba8743c8c19f39c)
- [Verified contract source](https://base-sepolia.blockscout.com/address/0x5F30276B3A5079E088Ec3072884286de5a868355?tab=contract)
- Machine-readable deployment evidence: `evidence/base-sepolia-deployment.json`

A real repeated-deployer `BLOCK` decision has also been recorded on-chain:

- [Decision receipt transaction](https://base-sepolia.blockscout.com/tx/0x13fdde4a65e27ad8dbe3843439f965eb0293dd630d0884e3b56c62eb43412eca)
- Decision hash: `0x4db586c8b62e13b6d110487664444439232355f39ba9f3cc824f50ecd18f1f6d`
- Memory evidence hash: `0xdf7f2cd0b47ebb70e43d0dfa9a8a3054e287bf35527b5f128d163507addb2a7a`
- Machine-readable receipt evidence: `evidence/base-sepolia-decision-receipt.json`
