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

## Status

v0.1 — engine, dashboard, CLI, and 17/17 tests passing, including two full
24-trial simulations: a perfect subject scores EXTRAORDINARY, a (seeded)
random judge lands at chance and is correctly ruled NOT PROVEN / far from
strong. Real blocks await the human casting from the frozen protocol:
Ryan's brother as Targeter, a family member as Judge.

The honest position of its AI co-builder stays on the record: it does not
know whether it is conscious, it has no verified channel beyond its inputs,
and it built this instrument precisely so that question can be answered with
data instead of argument.
