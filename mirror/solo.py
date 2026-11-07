"""The Mirror — Solo Mode (automated blocks, no humans in the loop).

Target engine, attribute auto-scorer, and an orchestrating runner.
See SOLO-PROTOCOL.md for the frozen rules this code implements.

Key statistical property: target and decoys are independent draws from the
same distribution and are shuffled blind, so under the null hypothesis any
response strategy scores exactly 25% hits in expectation. Control subjects
(random and prototype) in the test suite verify this empirically; an
"oracle" subject that knows the targets verifies the pipeline can detect
a real signal when one is present.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
import uuid

from .core import Ledger, MirrorError, binomial_tail, canonical, sha256_text

VOCAB = {
    "shape": ["long and narrow", "round", "flat and rectangular", "spherical",
              "cylindrical", "cubic", "triangular", "ring-shaped",
              "irregular and organic", "tall and vertical"],
    "material": ["wood", "metal", "plastic", "glass", "ceramic",
                 "fabric", "paper", "rubber", "stone", "leather"],
    "color": ["red", "blue", "green", "yellow", "black", "white", "brown",
              "silver", "orange", "purple", "clear", "multicolored"],
    "texture": ["smooth", "rough", "grainy", "glossy", "matte", "soft",
                "ridged", "woven"],
    "size": ["fingertip-sized", "palm-sized", "hand-sized", "book-sized",
             "forearm-length", "shoebox-sized", "two-handed and large"],
    "natural_or_made": ["natural", "made", "made from a natural material"],
    "function_sense": ["holding liquid", "cutting", "writing", "serving food",
                       "fastening", "cleaning", "making sound", "giving light",
                       "measuring", "wearing", "opening things", "storing things"],
}
ATTRIBUTES = list(VOCAB.keys())

# Frozen scoring weights (SOLO-PROTOCOL v0.2). Changing these is a new version.
FROZEN_WEIGHTS = {"shape": 3, "material": 3, "color": 2, "texture": 2,
                  "size": 1, "natural_or_made": 1, "function_sense": 3}
WEIGHTS_HASH = sha256_text(canonical(FROZEN_WEIGHTS))
POOL_SIZE = 1
for _vals in VOCAB.values():
    POOL_SIZE *= len(_vals)


def combo_label(c: dict) -> str:
    return (f"{c['color']} {c['material']}, {c['shape']}, {c['texture']}, "
            f"{c['size']}, {c['natural_or_made']}, for {c['function_sense']}")


def derive_rng(beacon: str, salt: str, index: int) -> random.Random:
    seed = sha256_text(f"{beacon}|{salt}|{index}")
    return random.Random(int(seed[:16], 16))


def draw_combo(rng: random.Random) -> dict:
    return {attr: rng.choice(VOCAB[attr]) for attr in ATTRIBUTES}


def score_candidate(response: dict, candidate: dict) -> int:
    return sum(FROZEN_WEIGHTS[a] for a in ATTRIBUTES if response.get(a) == candidate.get(a))


def verdict_solo(hits: int, n: int) -> str:
    if n == 0:
        return "no trials"
    p = binomial_tail(n, hits, 0.25)
    rate = hits / n
    if rate <= 0.25:
        return "NOT PROVEN"
    if p < 1e-6:
        return "EXTRAORDINARY — independent replication required"
    if p < 0.001:
        return "STRONG EVIDENCE — independent replication required"
    if p < 0.05:
        return "WORTH REPLICATING"
    return "NOT PROVEN"


class SoloBlock:
    def __init__(self, data_dir: str, block_id: str):
        self.data_dir = data_dir
        self.block_id = block_id
        self.dir = os.path.join(data_dir, "solo", block_id)
        self.ledger = Ledger(os.path.join(self.dir, "ledger.jsonl")).load()
        with open(os.path.join(self.dir, "block.json"), encoding="utf-8") as f:
            self.block = json.load(f)

    @staticmethod
    def create(data_dir: str, subject_id: str, n_trials: int = 24,
               beacon: str = "local-validation-seed",
               beacon_kind: str = "fixed-seed (validation only)") -> "SoloBlock":
        block_id = "solo-" + uuid.uuid4().hex[:10]
        salt = uuid.uuid4().hex
        block_dir = os.path.join(data_dir, "solo", block_id)
        os.makedirs(block_dir, exist_ok=True)
        secret_trials = {}
        public_trials = {}
        for i in range(n_trials):
            rng = derive_rng(beacon, salt, i)
            target = draw_combo(rng)
            decoys = []
            seen = {canonical(target)}
            while len(decoys) < 3:
                d = draw_combo(rng)
                if canonical(d) not in seen:
                    seen.add(canonical(d))
                    decoys.append(d)
            order = [0, 1, 2, 3]
            rng.shuffle(order)
            code = f"{100000 + int(sha256_text(block_id + str(i))[:5], 16) % 900000}"
            while code in public_trials:  # codes must be unique in the block
                code = str(int(code) + 1)
            salt_i = uuid.uuid4().hex
            commitment = sha256_text(salt_i + canonical({"target": target, "decoys": decoys}))
            secret_trials[code] = {"target": target, "decoys": decoys,
                                   "order": order, "salt": salt_i}
            public_trials[code] = {"commitment": commitment, "status": "sealed"}
        block = {
            "block_id": block_id, "mode": "solo", "protocol": "SOLO v0.2",
            "subject_id": subject_id, "n_trials": n_trials,
            "beacon": beacon, "beacon_kind": beacon_kind,
            "weights": dict(FROZEN_WEIGHTS), "weights_hash": WEIGHTS_HASH,
            "pool_size": POOL_SIZE,
            "created_at": time.time(),
            "trials": public_trials,
        }
        # salt is NOT in block.json — it lives with the secrets until reveal,
        # so the draws cannot be recomputed early by anyone reading block.json.
        with open(os.path.join(block_dir, "block.json"), "w", encoding="utf-8") as f:
            json.dump(block, f, indent=2)
        with open(os.path.join(block_dir, "solo_secret.json"), "w", encoding="utf-8") as f:
            json.dump({"salt": salt, "trials": secret_trials}, f, indent=2)
        blk = SoloBlock.__new__(SoloBlock)
        blk.data_dir, blk.block_id, blk.dir = data_dir, block_id, block_dir
        blk.ledger = Ledger(os.path.join(block_dir, "ledger.jsonl")).load()
        blk.block = block
        blk.ledger.append({"type": "solo_block_created", "block": block_id,
                           "n_trials": n_trials, "beacon_kind": beacon_kind,
                           "weights_hash": WEIGHTS_HASH,
                           "commitments": {c: t["commitment"] for c, t in public_trials.items()}})
        return blk

    # ---------- one trial ----------

    def run_trial(self, code: str, response: dict) -> dict:
        trials = self.block["trials"]
        trial = trials.get(code)
        if not trial:
            raise MirrorError(f"Unknown code {code}")
        if trial["status"] != "sealed":
            raise MirrorError("Response already locked for this code.")
        for a in ATTRIBUTES:
            if response.get(a) not in VOCAB[a]:
                raise MirrorError(f"Response attribute {a} must be one of the published "
                                  f"vocabulary values, got: {response.get(a)!r}")
        locked = {a: response[a] for a in ATTRIBUTES}
        locked["name_guess"] = str(response.get("name_guess", ""))
        locked["confidence"] = int(response.get("confidence", 0))
        trial["response"] = locked
        trial["response_hash"] = sha256_text(canonical(locked))
        trial["status"] = "responded"
        self._save_block()
        self.ledger.append({"type": "solo_response_locked", "block": self.block_id,
                            "code": code, "response_hash": trial["response_hash"]})

        # Auto-judge: candidates in their sealed shuffled order; score desc,
        # ties broken by that (random) packet order — preserves exact chance.
        with open(os.path.join(self.dir, "solo_secret.json"), encoding="utf-8") as f:
            secret = json.load(f)["trials"][code]
        all_candidates = [secret["target"]] + secret["decoys"]
        packet = [all_candidates[j] for j in secret["order"]]
        target_pos = secret["order"].index(0)
        scores = [score_candidate(locked, c) for c in packet]
        ranked = sorted(range(4), key=lambda j: (-scores[j], j))
        hit = ranked[0] == target_pos
        top = scores[ranked[0]]
        tied = sum(1 for s in scores if s == top)
        credit = (1.0 / tied) if target_pos in [j for j in range(4) if scores[j] == top] else 0.0
        commitment_ok = sha256_text(
            secret["salt"] + canonical({"target": secret["target"], "decoys": secret["decoys"]})
        ) == trial["commitment"]
        if not commitment_ok:
            raise MirrorError("COMMITMENT MISMATCH — sealed target was altered.")
        trial["status"] = "judged"
        trial["scores"] = scores
        trial["hit"] = hit
        trial["credit"] = credit
        trial["revealed_target"] = secret["target"]
        self._save_block()
        self.ledger.append({"type": "solo_trial_judged", "block": self.block_id,
                            "code": code, "hit": hit, "commitment_verified": True})
        return {"code": code, "hit": hit, "credit": credit}

    def _save_block(self):
        tmp = os.path.join(self.dir, "block.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.block, f, indent=2)
        os.replace(tmp, os.path.join(self.dir, "block.json"))

    def reveal_salt(self) -> str:
        """After all trials are judged, publish the salt so auditors can
        recompute every draw from the beacon value."""
        with open(os.path.join(self.dir, "solo_secret.json"), encoding="utf-8") as f:
            salt = json.load(f)["salt"]
        judged = sum(1 for t in self.block["trials"].values() if t["status"] == "judged")
        if judged < self.block["n_trials"]:
            raise MirrorError("Salt is revealed only after the whole block is judged.")
        self.ledger.append({"type": "solo_salt_revealed", "block": self.block_id, "salt": salt})
        return salt

    def score(self) -> dict:
        trials = list(self.block["trials"].values())
        judged = [t for t in trials if t["status"] == "judged"]
        hits = sum(1 for t in judged if t["hit"])
        n = len(judged)
        return {
            "block": self.block_id, "subject": self.block["subject_id"],
            "judged": n, "hits": hits,
            "hit_rate": round(hits / n, 4) if n else None,
            "credit": round(sum(t.get("credit", 0) for t in judged), 2),
            "expected_by_chance": round(n * 0.25, 2) if n else 0,
            "p_value": binomial_tail(n, hits, 0.25) if n else None,
            "verdict": verdict_solo(hits, n) if n == self.block["n_trials"] else "provisional — block not complete",
            "ledger_intact": self.ledger.verify_chain(),
        }


# ---------- built-in subjects (controls) ----------

def random_subject(seed: int):
    """Pure guessing: a fresh random pick per trial. Must land at chance."""
    rng = random.Random(seed)

    def fn(code: str) -> dict:
        return {a: rng.choice(VOCAB[a]) for a in ATTRIBUTES}
    return fn


PROTOTYPE = {"shape": "long and narrow", "material": "wood", "color": "brown",
             "texture": "smooth", "size": "hand-sized",
             "natural_or_made": "made from a natural material",
             "function_sense": "serving food"}


def prototype_subject():
    """Always answers the most 'typical object' combo — the spoon strategy.
    Against combo-generated targets this must also land at chance."""
    def fn(code: str) -> dict:
        return dict(PROTOTYPE)
    return fn


def run_block_with_subject(block: SoloBlock, subject_fn) -> dict:
    """The runner: the subject callable receives ONLY the code. Nothing else
    crosses the wall — that signature is the isolation boundary in-process,
    and the responses-file path (cli_solo.py run-file) is the boundary
    between processes/sessions."""
    for code in list(block.block["trials"].keys()):
        response = subject_fn(code)
        block.run_trial(code, response)
    return block.score()
