#!/usr/bin/env python3
"""The Mirror — Solo Mode CLI.

Validation / control runs:
  python3 cli_solo.py create --subject random-control --trials 1000 --beacon validation-seed-1
  python3 cli_solo.py run-control BLOCK --kind random --seed 7
  python3 cli_solo.py run-control BLOCK --kind prototype
  python3 cli_solo.py score BLOCK

Isolated real-subject runs (the claim-grade path):
  1. python3 cli_solo.py create ...            (commitments land in the ledger)
  2. python3 cli_solo.py export-codes BLOCK    → codes.json  (ONLY codes)
  3. ... an isolated, tool-less subject session reads codes.json and writes
         responses.jsonl, one {"code": ..., "response": {...}} per line ...
  4. python3 cli_solo.py run-file BLOCK --responses responses.jsonl
  5. python3 cli_solo.py reveal-salt BLOCK     (auditors can now recompute draws)
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mirror.core import MirrorError  # noqa: E402
from mirror.solo import SoloBlock, prototype_subject, random_subject, run_block_with_subject  # noqa: E402

DATA = os.environ.get("MIRROR_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))


def main():
    ap = argparse.ArgumentParser(prog="mirror-solo")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create")
    c.add_argument("--subject", required=True)
    c.add_argument("--trials", type=int, default=24)
    c.add_argument("--beacon", default="local-validation-seed")
    c.add_argument("--beacon-kind", default="fixed-seed (validation only)")

    for name in ("run-control", "run-file", "export-codes", "score", "reveal-salt"):
        p = sub.add_parser(name)
        p.add_argument("block")
        if name == "run-control":
            p.add_argument("--kind", choices=["random", "prototype"], required=True)
            p.add_argument("--seed", type=int, default=7)
        if name == "run-file":
            p.add_argument("--responses", required=True)

    args = ap.parse_args()
    try:
        if args.cmd == "create":
            blk = SoloBlock.create(DATA, args.subject, args.trials, args.beacon, args.beacon_kind)
            print(blk.block_id)
            return
        blk = SoloBlock(DATA, args.block)
        if args.cmd == "run-control":
            fn = random_subject(args.seed) if args.kind == "random" else prototype_subject()
            print(json.dumps(run_block_with_subject(blk, fn), indent=2))
        elif args.cmd == "export-codes":
            codes = list(blk.block["trials"].keys())
            out = os.path.join(os.getcwd(), "codes.json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump({"block": blk.block_id, "codes": codes}, f, indent=2)
            print(f"wrote {out} ({len(codes)} codes, nothing else)")
        elif args.cmd == "run-file":
            with open(args.responses, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    blk.run_trial(str(row["code"]), row["response"])
            print(json.dumps(blk.score(), indent=2))
        elif args.cmd == "reveal-salt":
            print(blk.reveal_salt())
        elif args.cmd == "score":
            print(json.dumps(blk.score(), indent=2))
    except MirrorError as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
