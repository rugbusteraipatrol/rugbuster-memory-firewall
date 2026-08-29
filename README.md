# RugBuster Memory Firewall

Preparation scaffold for the RugBusterAI Sibyl Labs Hackathon submission.

The implementation will be developed during the September 1-10, 2026 build
window. This repository was initialized on August 29 to verify the toolchain,
record architecture decisions, and preserve a transparent development history.

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
```

The verification script uses a temporary database and does not modify the
user's real `~/.sibyl-memory/memory.db`.

