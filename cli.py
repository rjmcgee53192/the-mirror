#!/usr/bin/env python3
"""The Mirror CLI — the role-separated workflow without the dashboard.

Examples:
  python3 cli.py create --title "Block 1" --subject "Automator" \
      --targeter "Jordan" --prompter "Ryan" --judge "Mom"
  python3 cli.py seal EXP --actor Jordan --code 481516 \
      --target "wooden salad spoon" --decoys "metal fork,plastic cup,wooden ruler"
  python3 cli.py respond EXP --actor Automator --code 481516 --json response.json
  python3 cli.py packet EXP --actor Mom --code 481516
  python3 cli.py judge EXP --actor Mom --code 481516 --ranking B,A,D,C
  python3 cli.py score EXP
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mirror.core import Experiment, MirrorError  # noqa: E402

DATA = os.environ.get("MIRROR_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data"))


def main():
    ap = argparse.ArgumentParser(prog="mirror")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create")
    for a in ("title", "subject", "targeter", "prompter", "judge"):
        c.add_argument("--" + a, required=True)
    c.add_argument("--trials", type=int, default=24)

    for name in ("seal", "respond", "packet", "judge", "score"):
        p = sub.add_parser(name)
        p.add_argument("exp")
        if name != "score":
            p.add_argument("--actor", required=True)
            p.add_argument("--code", required=True)
        if name == "seal":
            p.add_argument("--target", required=True)
            p.add_argument("--kind", default="object")
            p.add_argument("--decoys", required=True, help="comma-separated labels")
        if name == "respond":
            p.add_argument("--json", required=True, help="JSON file with fragments + confidence")
        if name == "judge":
            p.add_argument("--ranking", required=True, help="e.g. B,A,D,C best first")

    args = ap.parse_args()
    try:
        if args.cmd == "create":
            exp = Experiment.create(DATA, args.title, args.subject, args.targeter,
                                    args.prompter, args.judge, args.trials)
            print(exp.exp_id)
            return
        exp = Experiment(DATA, args.exp)
        if args.cmd == "seal":
            decoys = [{"label": d.strip()} for d in args.decoys.split(",") if d.strip()]
            print(json.dumps(exp.seal_trial(args.actor, args.code,
                                            {"label": args.target, "kind": args.kind}, decoys), indent=2))
        elif args.cmd == "respond":
            with open(args.json, encoding="utf-8") as f:
                payload = json.load(f)
            conf = payload.pop("confidence")
            print(json.dumps(exp.submit_response(args.actor, args.code, payload, conf), indent=2))
        elif args.cmd == "packet":
            print(json.dumps(exp.judge_packet(args.actor, args.code), indent=2))
        elif args.cmd == "judge":
            ranking = [x.strip().upper() for x in args.ranking.split(",") if x.strip()]
            print(json.dumps(exp.submit_judgement(args.actor, args.code, ranking), indent=2))
        elif args.cmd == "score":
            print(json.dumps(exp.score(), indent=2))
    except MirrorError as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
