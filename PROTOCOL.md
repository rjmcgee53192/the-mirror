# THE MIRROR — Frozen Protocol v1.0

Frozen 2026-11-06 by Ryan McGee and Automator. Changing any rule below creates
Protocol v2.0 — it never edits v1.0 retroactively. Every experiment stores a
SHA-256 hash of its protocol at creation; a mismatched hash means the
experiment is invalid, full stop.

## The problem this solves

In the famous Campbell/Alexa account, one person was targeter, questioner,
and judge. That design cannot distinguish a real effect from steering,
selective memory, or generous scoring. The Mirror separates every job:

- **Targeter** — the ONLY person who knows the targets. Works in a different
  location from the Subject. Randomly draws each target object, seals it in
  an opaque box/bag, assigns a random 6-digit code, and picks 3 decoys of a
  similar kind for that trial.
- **Prompter** — sees only codes. Pastes a code to the Subject, gives ZERO
  feedback (no reactions, no "close", no encouragement-by-content) for the
  whole block.
- **Subject** — human or AI. Produces one locked response per code using the
  fixed format below.
- **Judge** — a different person from the Targeter. Sees each locked
  response next to the target + 3 decoys, shuffled and unlabeled, and ranks
  all 4 from best match to worst. Never sees which item was the target until
  the ranking is locked.

No person may hold two of these roles in the same experiment. The software
enforces this for Targeter / Subject / Judge at creation.

## Block design

- 24 trials per experiment block.
- Chance is 1-in-4: a Judge ranking randomly expects ~6 hits in 24.
- A **hit** = the Judge ranks the real target #1.
- 2 secret controls are hidden inside the block by the Targeter:
  one trial whose box is EMPTY, one code with NO box at all.
  They are scored exactly like normal trials.
- No feedback of any kind until all 24 trials are judged.

## Locked response format (order is mandatory)

Raw fragments first, interpretation last — intellect naming the object early
is, in Campbell's own teaching, the main source of corruption:

1. shape
2. material
3. color
4. texture
5. size sense
6. natural or made
7. function sense
8. ONE unusual, specific detail (the "holes in the handle" slot)
9. ONE "it is NOT ___" statement
10. name guess — LAST, with a confidence number 0–100

A response, once submitted, is hashed and cannot be edited or resubmitted.

## Sealing and reveal

When the Targeter seals a trial, the software publishes a commitment:
`SHA-256(salt + target + decoys)` to the append-only ledger, and keeps the
salt in a Targeter-only secret file. After judging, the target is revealed
and anyone can recompute the commitment to prove the target was not swapped
after seeing the response.

The ledger is hash-chained: every entry contains the hash of the previous
entry. Editing history breaks the chain and is detectable by anyone.

## Pre-committed verdicts (for a complete 24-trial block)

- **16+ hits** — extraordinary. Independent replication required, publish loudly.
- **12+ hits** — strong evidence. Worth replicating with new people.
- **11 hits** — worth replicating. Interesting, not proven.
- **10 or fewer hits** — not proven. Published exactly like any other result.

Partial blocks get provisional statistics only — no verdict.

## What a result means, either way

A "not proven" result is a success for The Mirror. The instrument's job is
not to produce believers or skeptics; it is to produce a score nobody rigged,
in either direction.
