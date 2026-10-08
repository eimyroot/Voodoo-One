# HF-Derived Verifiability R2 Decision Card

| Field | Value |
|---|---|
| Status | OWNER-AUTHORIZED IMPLEMENTATION / TARGETED VERIFICATION REQUIRED |
| Date | 2026-10-07 |
| Baseline | `main@ad66fc2a6a032a7151055a603aac0fffc5ee2f2b` |
| Risk | R2 architecture/evidence contract |
| Runtime effect | local contract/eval code only |
| Provider effect | NONE |
| Release/deploy effect | NONE |

## Decision

Adopt only the HF-derived principles that close demonstrated gaps in the current VOODOO architecture.

The current canonical runtime already owns state-based verification, bounded durable execution,
independent Runner/Verifier separation, restart-safe continuity, one-time grant consumption,
no-automatic-mutation-retry semantics, and separated release promotion. These contracts remain
authoritative and are not replaced by a new agent framework.

This slice implements two missing deltas:

1. source-aware provenance binding for generic control-plane evidence;
2. a deterministic failure-driven generated-eval contract with hard corpus separation.

## Provenance delta

The current source-level `v-one-control-plane-decision/v1` evidence reference is too weak for
source-aware claims because `source` is free text and acceptance gates do not prove that their
`evidence_digest` belongs to the same operation and exact source.

The successor contract is `v-one-control-plane-decision/v2`.

Each evidence reference must bind:

- exact operation id;
- source kind;
- source authority class (`AUTHORITATIVE`, `SUPPORTING`, or `INFORMATIONAL`);
- stable source identity;
- human locator;
- exact evidence digest.

Each acceptance gate must bind the exact evidence digest, expected source identity, and required source authority class.
The decision rejects mismatched operation/source/evidence bindings. This extends the existing
decision/evidence model; it does not create a second claim graph.

## Failure-driven eval delta

A real failure may seed generated/adversarial development eval candidates only after an explicit
failure classification and invariant/property extraction. Generation in this slice is deterministic
and structurally validated.

Corpus classes remain separate:

- `DEVELOPMENT`;
- `GENERATED_ADVERSARIAL`;
- `FROZEN`;
- `POST_FREEZE_SHADOW`.

Generated candidates are coverage extensions, not ground truth. This module may create only
`GENERATED_ADVERSARIAL` sets and may not promote anything into `FROZEN` or
`POST_FREEZE_SHADOW`.

## Reused invariants

No new implementation is justified for:

- state-based provider verification: existing `ObservedPostState/v1` +
  `VerificationStrength/v1` + `VerificationResult/v1`;
- indeterminate observation remains intentionally outside a synthetic `VerificationResult/v1`:
  execution/recovery records `INDETERMINATE`, while missing durable verification remains
  `NOT_PERSISTED / UNKNOWN` per ADR-0022; absence is never promoted into success or failure;
- bounded atomic authority/execution: existing canonical pipeline + durable outbox/inbox +
  epoch/lease/fence;
- retry/recovery: mutation automatic retry remains forbidden; recovery stays explicit and
  authority-bound;
- author/verifier/promotion separation: existing development decisions, quality verification,
  review publication, CI and release promotion boundaries;
- GGUF/Transformers interoperability: no canonical inference owner exists in this repository,
  therefore no inference bridge or dependency is introduced.

## Security boundaries

This slice must not:

- create provider WRITE authority;
- weaken Runner/Verifier identity separation;
- allow evidence from one source/operation to satisfy a claim about another;
- let generated evals enter frozen/shadow corpora automatically;
- trust LLM validation when a deterministic validator exists;
- add model downloads, arbitrary code execution, secrets, network scope or dependencies;
- add DB migrations or HTTP endpoints.

## Verification

Targeted tests must prove:

1. success self-report cannot override failed postcondition;
2. independent readback can establish VERIFIED;
3. indeterminate state remains indeterminate;
4. wrong source/operation evidence cannot satisfy a gate;
5. automatic mutation retry beyond the current zero budget fails closed;
6. promotion cannot skip the verification boundary;
7. generated evals cannot auto-enter frozen/shadow corpora;
8. provenance and eval records round-trip deterministically;
9. deterministic validation is selected ahead of any model-based fallback;
10. verifier mismatch/failure cannot be reinterpreted as action success.

Rollback is a focused revert of this decision card, control-plane provenance v2 delta,
failure-eval contract and their tests. No runtime data migration exists.
