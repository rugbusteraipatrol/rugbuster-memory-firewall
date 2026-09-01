# Architecture decisions

## Scope

- V1 supports AVAX and Solana creator identity because existing RugBuster data
  has useful creator coverage for those chains.
- BNB, Base, and TRON are out of scope until creator resolution is reliable.
- A caller-supplied deployer is optional and must be verified when a resolver
  can independently determine it.
- An unresolved or conflicting deployer fails closed.

AVAX creator resolution uses Routescan's `getcontractcreation` result and
validates the returned contract, creator, and creation transaction hash. Solana
uses only RugCheck's top-level `creator`/`deployer`; a market-level deployer is
not accepted as identity evidence.

## Evidence levels

- Scanner labels are historical risk signals, not allegations or proof.
- One independently verified critical event may produce
  `BLOCK` with reason code `BLOCK_REPEAT_DEPLOYER`.
- Two or more distinct historical warnings may produce
  `WARN` with reason code `WARN_REPEATED_PATTERN`.
- No final ALLOW, WARN, or BLOCK verdict is possible when Sibyl Memory cannot
  be read; the only result is `MEMORY_REQUIRED`.

## Memory tiers

- HOT: analysis currently in progress.
- WARM: current creator/deployer risk state.
- COLD: append-only application journal of observations and decisions.
- REFERENCE: versioned policy rules and trusted source definitions.

Only four top-level verdicts exist: `ALLOW`, `WARN`, `BLOCK`, and
`MEMORY_REQUIRED`. Detailed explanations are stable reason codes. AVAX/EVM
addresses are normalized to lowercase; Solana addresses remain case-sensitive.
Every decision includes the token address and canonical action hash so it cannot
be reused as authorization for a different proposed action.

The COLD journal is append-only by application design. It is not described as
cryptographically immutable. A Base Sepolia receipt can anchor decision and
memory-evidence hashes separately.

## Build-window transparency

The repository scaffold, dependency verification, and architecture notes were
created on August 29, 2026. Core hackathon functionality is developed during
the published September 1-10 build window. Prior RugBuster assets are declared
in the README instead of being presented as new work.
