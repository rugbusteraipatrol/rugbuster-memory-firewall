# Demo script - target 3:20

The fresh-session section must be one continuous, unedited screen recording.
Keep a UTC clock and the current Git commit visible in the terminal.

## 0:00-0:25 - Problem

"A token can look clean right now while its deployer has harmful verified
history on other contracts. Stateless scanners forget that history between
sessions. RugBuster Memory Firewall remembers it before an action is signed."

Show the proposed action and the clean current signal. Do not begin with slides.

## 0:25-0:55 - Verified historical evidence

Show the two historical token addresses, common deployer, and the public WAVAX
transaction facts. Run the live verifier so the evidence is re-queried rather
than read from a prepared conclusion.

## 0:55-1:55 - Unedited load-bearing moment

In one continuous segment:

1. Show UTC time and `git rev-parse --short HEAD`.
2. Write the verified observations through client/session A.
3. Close session A.
4. Start fresh client/session B against the same Sibyl database.
5. Analyze the different recall-target token with clean current signals.
6. Hold on the output: `BLOCK`, `BLOCK_REPEAT_DEPLOYER`, evidence count `2`.

Say: "The current signal is clean. The decision changes only because the fresh
session recalled verified deployer history from Sibyl Memory."

## 1:55-2:20 - Deletion test

Run the single deletion test and show `PASSED`.

Say: "When Sibyl Memory is removed, the agent does not silently allow the
action. It returns `MEMORY_REQUIRED`, so the core history-aware firewall no
longer functions."

## 2:20-2:50 - Architecture

Show the four memory tiers briefly: HOT analysis, WARM deployer entity, COLD
journal, REFERENCE policy. Point to the mandatory read and deterministic policy
branch. Do not scroll through unrelated code.

## 2:50-3:15 - Base action

Show the executed `recordDecision` interaction and open the Blockscout receipt.
Match the on-chain memory hash to the fresh-session output.

Say: "Base makes the decision auditable outside our process. The receipt binds
the verdict to the exact memory evidence and policy version."

## 3:15-3:20 - Close

"RugBuster gives wallets and agents a memory-aware safety gate before they act."

## Recording rules

- Use 1080p, large terminal text, and no background music over speech.
- No cuts during fresh-session recall.
- Keep the pointer still while the judge reads the verdict and hashes.
- Never call an unverified token name or wallet a scammer.
- Do not spend time on installation, generic architecture slides, or feature
  lists that are not exercised.
