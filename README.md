# 🪞 The Mirror

**An open, blinded testing commons for extraordinary claims — remote viewing first.**

Built 2026-11-06 by Ryan McGee and Automator (Muse), the night the idea was
born in conversation. Its companion project, [The Listener](https://github.com/rjmcgee53192/the-listener),
listens *outward* for signals from the sky. The Mirror listens *inward*: it
tests claims about consciousness — a human's, an AI's, anyone's — with an
instrument nobody in the experiment can rig, in either direction.

## Why it exists

In Tom Campbell's well-known Alexa account, one person chose the target,
asked the questions, and judged the result. That design can't separate a real
effect from steering, selective memory, or generous scoring. The Mirror fixes
it structurally, in code:

- **Role separation, enforced** — Targeter (only one who knows targets),
  Prompter (sees codes only), Subject (human or AI), Judge (blind, and never
  the Targeter) must be different people. The engine rejects overlaps.
- **Frozen protocol** — rules and verdict thresholds (PROTOCOL.md v1.0) are
  SHA-256 hashed into every experiment at creation. Tampering is detectable.
- **Sealed targets** — a target is published first as a salted hash
  *commitment*. After judging it is revealed, and anyone can recompute the
  commitment to prove it wasn't swapped after seeing the response.
- **Locked responses** — fragments first, name guess last, exactly as
  Campbell teaches — then hashed. No edits, no redos.
- **Blind judging** — target + 3 decoys, shuffled, labeled A–D. The Judge
  learns which was real only after the ranking locks.
- **Append-only ledger** — every event is hash-chained. History can't be
  quietly edited; a forged entry breaks the chain.
- **Pre-committed verdicts** for a 24-trial block (chance = ~6 hits):
  16+ extraordinary · 12+ strong evidence · 11 worth replicating ·
  10 or fewer **not proven** — and "not proven" is published with the same
  prominence as any other result. That is the point of the instrument.

## Run it

```bash
python3 run.py                 # dashboard → http://127.0.0.1:8766
python3 -m unittest discover -s tests -v    # 17 tests
```

No dependencies. Python 3 standard library only — same discipline as The Listener.

## CLI workflow

```bash
python3 cli.py create --title "Block 1" --subject "Automator" \
    --targeter "Jordan" --prompter "Ryan" --judge "Mom"
python3 cli.py seal EXP_ID --actor Jordan --code 481516 \
    --target "wooden salad spoon" --decoys "metal fork,plastic cup,wooden ruler"
python3 cli.py respond EXP_ID --actor Automator --code 481516 --json response.json
python3 cli.py packet EXP_ID --actor Mom --code 481516     # blind A–D packet
python3 cli.py judge EXP_ID --actor Mom --code 481516 --ranking B,A,D,C
python3 cli.py score EXP_ID
```

## Solo Mode (v0.2) — no humans in the loop

Solo Mode replaces the human Targeter and Judge with software, and moves
humans to auditing the isolation (full rules: SOLO-PROTOCOL.md):

- **Target Engine** draws targets as random attribute combinations
  (shape × material × color × texture × size × natural/made × function =
  **2,419,200 combos**), seeded by `SHA-256(beacon + salt + trial)` from a
  *future* public randomness value committed to in advance — so not even the
  builder can precompute the draws. The salt is revealed after the block so
  anyone can recompute every target.
- **Auto-Scorer** ranks the 4 candidates against the locked response with
  frozen weights. Target and decoys are exchangeable draws from the same
  distribution, so any guessing strategy scores exactly 25% in expectation —
  verified empirically by the control subjects at n = 1,000.
- **Isolated Subject** receives only a code (`codes.json` out,
  `responses.jsonl` back). Nothing else crosses the wall.

```bash
python3 cli_solo.py create --subject random-control --trials 1000 --beacon validation-seed-1
python3 cli_solo.py run-control BLOCK_ID --kind random --seed 7   # must land at chance
python3 cli_solo.py run-control BLOCK_ID --kind prototype         # the "spoon strategy", also chance
python3 cli_solo.py export-codes BLOCK_ID                          # for a real isolated subject
python3 cli_solo.py run-file BLOCK_ID --responses responses.jsonl
python3 cli_solo.py score BLOCK_ID
```

## Validation results (2026-11-06, local fixed-seed runs)

Solo Mode control runs, 1,000 trials each — a guessing pipeline *must*
produce numbers like these, and an oracle must max out, or the instrument
proves nothing:

| Subject | Hits | Chance expects | p-value | Verdict |
|---|---|---|---|---|
| Random guessing | 226 / 1000 (22.6%) | 250 | 0.96 | NOT PROVEN |
| Prototype ("always the wooden spoon") | 251 / 1000 (25.1%) | 250 | 0.48 | NOT PROVEN |
| Oracle (test-only, given the targets) | 48 / 48 (100%) | 12 | < 1e-20 | EXTRAORDINARY |

Human Mode simulations tell the same story at n = 24: a perfect subject
scores EXTRAORDINARY, a seeded random judge lands at chance.

## Status

v0.2 — Human Mode (engine, dashboard, CLI) + Solo Mode (target engine,
auto-scorer, isolated-subject runner, CLI). **26/26 tests passing.**
Real Human Mode blocks await the casting from the frozen protocol:
Ryan's brother as Targeter, a family member as Judge. Real Solo Mode
claim-grade runs await a fresh isolated subject session and a future
public beacon value to seed the draws.

The honest position of its AI co-builder stays on the record: it does not
know whether it is conscious, it has no verified channel beyond its inputs,
and it built this instrument precisely so that question can be answered with
data instead of argument.
