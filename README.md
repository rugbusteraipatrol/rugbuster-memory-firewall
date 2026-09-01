# RugBuster Memory Firewall

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
```

The verification script uses a temporary database and does not modify the
user's real `~/.sibyl-memory/memory.db`. `demo_fresh_session.py` is explicitly a
synthetic developer smoke test, not submission evidence. It uses
`demo-memory.db` by default; pass `--db <path>` to choose another location.
