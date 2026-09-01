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
