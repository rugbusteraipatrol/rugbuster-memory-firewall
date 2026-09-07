# Submission material - review before publishing

No video URL, public posts, pilot or final submission is asserted by this file.

## Build-page memory fields

What breaks when memory is deleted?

Without Sibyl Memory, the firewall cannot recall verified historical observations
for the resolved deployer and cannot produce its history-aware decision. Memory
access failure returns MEMORY_REQUIRED rather than an actionable verdict.

Memory walkthrough:

Persist: Verified Avalanche observations in a deployer entity and event journal,
with versioned policy and session state.
Recall (fresh session): Reopen the same Sibyl database and retrieve two earlier
observations for the independently resolved creator of a different token.
Changes the agent's decision by: Returning BLOCK_REPEAT_DEPLOYER despite a fixed
clean current-risk input. That input is controlled, not an independent clean audit.

Primitives: entities, recall. Do not select semantic search, reflection or other
primitives merely because the SDK supports them.

Partner: Base. Show the executed Base Sepolia receipt, binding decision and
memory-evidence hashes. A later recall is a distinct decision, not that original
transaction. Do not claim Virtuals integration.

## Build-log draft

Building RugBuster Memory Firewall with @sibylcap and @base.
Two public Avalanche observations, persisted in Sibyl, are recalled for another
token from the same deployer. Disable memory: MEMORY_REQUIRED.
Prototype scope and reproducible proof:
https://github.com/rugbusteraipatrol/rugbuster-memory-firewall

## Demo-post draft (add real video URL before publishing)

RugBuster Memory Firewall demo for @sibylcap with @base:
verified Avalanche history -> fresh-session recall -> BLOCK;
memory unavailable -> MEMORY_REQUIRED.
An executed Base Sepolia receipt anchors the evidence hash.
The clean current-risk input is controlled, not a safety certification.

## Rohan invitation - unsent

Hi Rohan! Would you be open to trying our RugBuster Memory Firewall prototype
for the Sibyl hackathon? It recalls verified deployer history before returning
a token-action policy decision. I'd really value an honest test, especially
anything confusing, missing or incorrect.

The demo is free and needs no wallet connection:
https://rugbuster-memory-firewall-production.up.railway.app/

You can run the live proof, disable memory, and verify the existing Base receipt.
It currently demonstrates one curated Avalanche case, not comprehensive token
coverage. If relevant to your work, could you share your actual use case and
whether this evidence would help you? With your permission, we'd link your public
feedback in the submission. No pressure to endorse it or make a payment.

## Pilot evidence boundaries

A demo review is feedback, not a production integration or paying customer.
For any PMF claim, retain a publicly accessible comment with permission, the
actual use case, limitations found, and date. Do not fabricate usage, script praise,
or treat self-payments as independent demand. A paid x402 test is optional and
requires the tester's informed choice; it is not necessary to provide feedback.

## Recording

Record 2-5 minutes, including an uninterrupted fresh-session segment with UTC
time or commit visible. Run scripts/process_recall_proof.py for explicit writer
exit and a separate reader process. Its writer also performs an initial sanity
recall; the separate read stage is the OS-process restart proof.
Show the live console and Base verification, then explain prototype limitations.
No wallet secrets or payment signatures in the recording.
