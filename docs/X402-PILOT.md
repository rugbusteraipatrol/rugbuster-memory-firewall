# Independent x402 pilot

The PMF claim is complete only after a person outside the RugBuster team makes
a real paid request. A self-payment is useful engineering QA, but it is not
independent product evidence.

## Public offer

- Resource: `POST /v1/x402/pre-sign`
- Price: `$0.01` USDC
- Settlement network: Base mainnet (`eip155:8453`)
- Protocol: x402 v2, `exact`
- Output: verdict, recalled deployer history, reason codes, evidence sources,
  `decision_hash`, and `memory_evidence_hash`

An unpaid request must return HTTP `402` with a `PAYMENT-REQUIRED` header. A
valid `PAYMENT-SIGNATURE` is verified and settled by Coinbase CDP before the
successful response is returned.

## Evidence checklist

1. Invite one named pilot in the Sibyl Discord to test a token action they
   actually care about.
2. Let the pilot's own x402-capable agent make the `$0.01` request. Do not send
   funds to the pilot and do not make the request from a RugBuster wallet.
3. Preserve the Base payment transaction from `PAYMENT-RESPONSE` and the
   server's append-only settlement log.
4. Ask for a short public comment stating the use case and whether the verdict
   was useful. Do not script a positive opinion for them.
5. Publish one redacted case artifact linking the payment transaction,
   `decision_hash`, `memory_evidence_hash`, request purpose, and public comment.

The runtime log intentionally excludes the payment signature, CDP credentials,
and full request body. It records only public settlement data and RugBuster's
two evidence hashes.

## Suggested invitation

> Hi! We built a memory-backed pre-sign firewall for the Sibyl hackathon. It
> remembers verified deployer history across sessions and can block a new token
> even when its current signals look clean. We now have a real x402 endpoint on
> Base priced at $0.01 USDC. Would you be willing to try one token/action you
> genuinely care about and share one honest sentence about whether the result
> was useful? We will credit you only if you want to be named.
