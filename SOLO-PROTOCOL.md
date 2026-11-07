# THE MIRROR — Solo Mode Protocol v0.2 (Automated Blocks)

Solo Mode removes humans from the loop *during* a block. Humans move to a
different job: auditing the isolation. This document is frozen the same way
PROTOCOL.md is — changes create a new version, never a retroactive edit.

## Roles, replaced

- **Targeter → Target Engine.** Targets are not household objects picked by
  a person (people pick prototypes, and prototypes are guessable). A target
  is a random combination drawn from published vocabularies:
  shape × material × color × texture × size × natural/made × function —
  2,419,200 possible combinations in v0.2. There is no "typical" target.
- **Judge → Attribute Auto-Scorer.** Frozen weights (below) score the locked
  response against each of the 4 candidates by exact attribute match.
  No generosity, no mood, fully reproducible by any auditor.
- **Subject → an isolated session.** It receives ONLY a 6-digit code per
  trial and returns attribute picks from the same published vocabularies
  (plus the usual free-text slots, which the auto-scorer ignores and human
  auditors may read). It has no file access, no tools, no internet.
- **Prompter → the Runner.** Orchestrates trials, locks and hashes every
  response before any reveal, and writes the hash-chained ledger.

## Randomness you cannot precompute

Before a block, the experiment commits in writing to a *future* public
randomness value (e.g. a NIST Randomness Beacon pulse at a named timestamp,
or a drand round). Draws are seeded by `SHA-256(beacon_value + block_salt +
trial_index)`. Consequences:

- Before the beacon publishes, nobody — not even the builder of this
  software — can know or steer the draws.
- After the block, the salt is revealed and any auditor can recompute every
  draw and confirm the targets were exactly what the seed produced.

For local validation runs, a recorded fixed seed string is used instead and
is labeled as such; those runs prove the *pipeline*, not any claim.

## Exchangeability (why chance stays exactly 1-in-4)

Target and 3 decoys are independent draws from the same distribution,
shuffled blind. Under the null hypothesis (the subject has no anomalous
information), every candidate is equally likely to best-match ANY response
strategy — random guessing, always answering "wooden brown spoon", anything.
Ties in score are broken by the sealed shuffle order, which is also random.
So a guessing subject MUST land at ~25% hits over a large block, and the
binomial test stays exact. The control runs in the test suite demonstrate
this empirically at n = 1,000.

## Isolation requirements for a claim-grade run

1. Commitments for all trials are written to the ledger (and, for public
   runs, pushed to the public GitHub repo) BEFORE the subject session starts.
2. The subject session is fresh, tool-less, and cannot read the block folder.
   In practice: it is handed a `codes.json` file containing only codes, and
   hands back a `responses.jsonl`. Nothing else crosses the wall.
3. The block's secret file (targets + salt) lives outside any directory the
   subject session can reach.
4. After the run: reveal, recompute commitments and draws, publish everything.

A result from a setup that skips these steps is a *practice* result, and the
ledger says so.

## Verdicts for Solo blocks (large-n)

Solo blocks are judged by statistics, not the fixed 24-trial table:

- p ≥ 0.05 → NOT PROVEN
- p < 0.05 → WORTH REPLICATING
- p < 0.001 → STRONG EVIDENCE (replication on an independent machine required)
- p < 0.000001 → EXTRAORDINARY (independent replication required, loudly)

...where p is the exact binomial tail against chance = 0.25. Effect size
(hit rate) is always reported alongside p; tiny effects at huge n are
reported as tiny, not dressed up.

## Known limit, stated plainly

The target exists as data on a machine. Isolation and cryptography are the
controls for that — not physical distance, as in Human Mode. A claim-grade
Solo result therefore always requires independent replication on a machine
the original builders do not control. That is a feature: the repo is the
instrument, and anyone can run it.
