# Architecture decisions

## Scope

- V1 supports AVAX and Solana creator identity because existing RugBuster data
  has useful creator coverage for those chains.
- BNB, Base, and TRON are out of scope until creator resolution is reliable.
- A caller-supplied deployer is optional and must be verified when a resolver
  can independently determine it.
- An unresolved or conflicting deployer fails closed.

## Evidence levels

- Scanner labels are historical risk signals, not allegations or proof.
- One independently verified critical event may produce
  `BLOCK_REPEAT_DEPLOYER`.
- Two or more distinct historical warnings may produce
  `WARN_REPEATED_PATTERN`.
- No final ALLOW, WARN, or BLOCK verdict is possible when Sibyl Memory cannot
  be read; the only result is `MEMORY_REQUIRED`.

## Memory tiers

- HOT: analysis currently in progress.
- WARM: current creator/deployer risk state.
- COLD: append-only application journal of observations and decisions.
- REFERENCE: versioned policy rules and trusted source definitions.

The COLD journal is append-only by application design. It is not described as
cryptographically immutable. A Base Sepolia receipt can anchor decision and
memory-evidence hashes separately.

## Build-window transparency

The repository scaffold, dependency verification, and architecture notes were
created on August 29, 2026. Core hackathon functionality is developed during
the published September 1-10 build window. Prior RugBuster assets are declared
in the README instead of being presented as new work.

