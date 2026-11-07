"""The Mirror — core engine.

A blinded testing commons for extraordinary claims (remote viewing first).

Design rules, enforced here in code, not just promised in docs:
  * Roles are separated: targeter / subject / judge must be different people.
  * A protocol is frozen by SHA-256 hash at experiment creation.
  * A target is sealed as a salted hash commitment BEFORE any response exists.
  * A subject response is hashed and locked; it cannot be edited or redone.
  * A judge sees target+decoys shuffled and unlabeled, and learns which item
    was the target only AFTER the ranking is locked.
  * Every event is written to an append-only, hash-chained ledger.
  * Verdict thresholds are pre-committed in the protocol (see PROTOCOL.md).
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import secrets
import time
import uuid
from dataclasses import dataclass, field

RESPONSE_FIELDS = [
    "shape", "material", "color", "texture", "size",
    "natural_or_made", "function_sense", "unusual_detail",
    "not_statement", "name_guess",
]

DEFAULT_THRESHOLDS = {"extraordinary": 16, "strong": 12, "replicate": 11}


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def binomial_tail(n: int, k: int, p: float = 0.25) -> float:
    """P(X >= k) for X ~ Binomial(n, p). The chance a random judge does this well."""
    if k <= 0:
        return 1.0
    total = 0.0
    for i in range(k, n + 1):
        total += math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i))
    return total


def verdict_for(hits: int, judged: int, planned: int, thresholds=None) -> str:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    if judged < planned:
        return "provisional — block not complete, no verdict"
    if hits >= thresholds["extraordinary"]:
        return "EXTRAORDINARY — independent replication required"
    if hits >= thresholds["strong"]:
        return "STRONG EVIDENCE — worth replicating with new people"
    if hits >= thresholds["replicate"]:
        return "WORTH REPLICATING — interesting, not proven"
    return "NOT PROVEN — published like any other result"


class MirrorError(Exception):
    pass


@dataclass
class Ledger:
    path: str
    entries: list = field(default_factory=list)

    def load(self):
        self.entries = []
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.entries.append(json.loads(line))
        return self

    def append(self, event: dict) -> dict:
        prev = self.entries[-1]["entry_hash"] if self.entries else "GENESIS"
        entry = {"ts": time.time(), "prev_hash": prev, **event}
        entry["entry_hash"] = sha256_text(prev + canonical({k: v for k, v in entry.items() if k != "entry_hash"}))
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(canonical(entry) + "\n")
        self.entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        prev = "GENESIS"
        for e in self.entries:
            body = {k: v for k, v in e.items() if k != "entry_hash"}
            if e.get("prev_hash") != prev:
                return False
            if sha256_text(prev + canonical(body)) != e.get("entry_hash"):
                return False
            prev = e["entry_hash"]
        return True


class Experiment:
    """One 24-trial block, stored as a folder under the data dir."""

    def __init__(self, data_dir: str, exp_id: str):
        self.data_dir = data_dir
        self.exp_id = exp_id
        self.dir = os.path.join(data_dir, "experiments", exp_id)
        self.ledger = Ledger(os.path.join(self.dir, "ledger.jsonl")).load()
        with open(os.path.join(self.dir, "protocol.json"), encoding="utf-8") as f:
            self.protocol = json.load(f)
        state_path = os.path.join(self.dir, "state.json")
        if os.path.exists(state_path):
            with open(state_path, encoding="utf-8") as f:
                self.state = json.load(f)
        else:
            self.state = {"trials": {}}

    # ---------- creation / freezing ----------

    @staticmethod
    def create(data_dir: str, title: str, subject: str, targeter: str,
               prompter: str, judge: str, n_trials: int = 24,
               decoys_per_trial: int = 3) -> "Experiment":
        people = {"subject": subject, "targeter": targeter, "judge": judge}
        lowered = {k: v.strip().lower() for k, v in people.items()}
        if len(set(lowered.values())) < 3:
            raise MirrorError("Roles cannot overlap: subject, targeter and judge "
                              "must be three different people.")
        if prompter.strip().lower() == targeter.strip().lower():
            raise MirrorError("Prompter must not be the targeter (prompter must not know targets).")
        if n_trials < 1 or decoys_per_trial < 1:
            raise MirrorError("Need at least 1 trial and 1 decoy.")
        exp_id = "exp-" + uuid.uuid4().hex[:10]
        protocol = {
            "version": "1.0",
            "title": title,
            "subject": subject, "targeter": targeter,
            "prompter": prompter, "judge": judge,
            "n_trials": n_trials,
            "decoys_per_trial": decoys_per_trial,
            "chance": 1.0 / (decoys_per_trial + 1),
            "thresholds": dict(DEFAULT_THRESHOLDS),
            "response_fields": list(RESPONSE_FIELDS),
            "created_at": time.time(),
        }
        protocol["protocol_hash"] = sha256_text(canonical(
            {k: v for k, v in protocol.items() if k != "protocol_hash"}))
        exp_dir = os.path.join(data_dir, "experiments", exp_id)
        os.makedirs(exp_dir, exist_ok=True)
        with open(os.path.join(exp_dir, "protocol.json"), "w", encoding="utf-8") as f:
            json.dump(protocol, f, indent=2)
        with open(os.path.join(exp_dir, "state.json"), "w", encoding="utf-8") as f:
            json.dump({"trials": {}}, f)
        exp = Experiment.__new__(Experiment)
        exp.data_dir, exp.exp_id, exp.dir = data_dir, exp_id, exp_dir
        exp.ledger = Ledger(os.path.join(exp_dir, "ledger.jsonl")).load()
        exp.protocol = protocol
        exp.state = {"trials": {}}
        exp.ledger.append({"type": "protocol_frozen", "exp": exp_id,
                           "protocol_hash": protocol["protocol_hash"]})
        return exp

    @staticmethod
    def list_ids(data_dir: str):
        root = os.path.join(data_dir, "experiments")
        if not os.path.isdir(root):
            return []
        return sorted(d for d in os.listdir(root)
                      if os.path.isdir(os.path.join(root, d)))

    def check_protocol_integrity(self) -> bool:
        body = {k: v for k, v in self.protocol.items() if k != "protocol_hash"}
        return sha256_text(canonical(body)) == self.protocol.get("protocol_hash")

    def _save_state(self):
        tmp = os.path.join(self.dir, "state.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
        os.replace(tmp, os.path.join(self.dir, "state.json"))

    def _secret_path(self):
        return os.path.join(self.dir, "targeter_secret.json")

    def _load_secret(self):
        p = self._secret_path()
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_secret(self, secret):
        tmp = self._secret_path() + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(secret, f, indent=2)
        os.replace(tmp, self._secret_path())

    # ---------- targeter: seal a trial ----------

    def seal_trial(self, actor: str, code: str, target: dict, decoys: list) -> dict:
        if actor.strip().lower() != self.protocol["targeter"].strip().lower():
            raise MirrorError("Only the targeter may seal trials.")
        code = str(code).strip()
        if not (code.isdigit() and len(code) == 6):
            raise MirrorError("Code must be exactly 6 digits.")
        if code in self.state["trials"]:
            raise MirrorError(f"Code {code} is already sealed.")
        if len(self.state["trials"]) >= self.protocol["n_trials"]:
            raise MirrorError("Block is full — all trials already sealed.")
        if len(decoys) != self.protocol["decoys_per_trial"]:
            raise MirrorError(f"Need exactly {self.protocol['decoys_per_trial']} decoys.")
        if not target.get("label"):
            raise MirrorError("Target needs a label.")
        salt = secrets.token_hex(16)
        commitment = sha256_text(salt + canonical({"target": target, "decoys": decoys}))
        secret = self._load_secret()
        secret[code] = {"salt": salt, "target": target, "decoys": decoys}
        self._save_secret(secret)
        self.state["trials"][code] = {"status": "sealed", "commitment": commitment}
        self._save_state()
        self.ledger.append({"type": "trial_sealed", "exp": self.exp_id,
                            "code": code, "commitment": commitment})
        return {"code": code, "commitment": commitment}

    # ---------- subject: lock a response ----------

    def submit_response(self, actor: str, code: str, fragments: dict, confidence: int) -> dict:
        if actor.strip().lower() != self.protocol["subject"].strip().lower():
            raise MirrorError("Only the subject may submit responses.")
        code = str(code).strip()
        trial = self.state["trials"].get(code)
        if not trial:
            raise MirrorError(f"Code {code} is not sealed.")
        if trial["status"] != "sealed":
            raise MirrorError("A response is already locked for this code — responses cannot be redone.")
        missing = [k for k in RESPONSE_FIELDS if not str(fragments.get(k, "")).strip()]
        if missing:
            raise MirrorError("Response is missing required fragments: " + ", ".join(missing))
        if not (0 <= int(confidence) <= 100):
            raise MirrorError("Confidence must be 0–100.")
        locked = {k: str(fragments[k]).strip() for k in RESPONSE_FIELDS}
        locked["confidence"] = int(confidence)
        resp_hash = sha256_text(canonical(locked))
        trial["status"] = "responded"
        trial["response"] = locked
        trial["response_hash"] = resp_hash
        self._save_state()
        self.ledger.append({"type": "response_locked", "exp": self.exp_id,
                            "code": code, "response_hash": resp_hash})
        return {"code": code, "response_hash": resp_hash}

    # ---------- judge: blind packet + ranking ----------

    def judge_packet(self, actor: str, code: str) -> dict:
        if actor.strip().lower() != self.protocol["judge"].strip().lower():
            raise MirrorError("Only the judge may open a judge packet.")
        code = str(code).strip()
        trial = self.state["trials"].get(code)
        if not trial or trial["status"] != "responded":
            raise MirrorError("Judge packet is available only after a response is locked.")
        secret = self._load_secret()[code]
        items = [{"label": secret["target"]["label"], "kind": "target"}] + \
                [{"label": d["label"], "kind": "decoy"} for d in secret["decoys"]]
        rng = random.Random(secrets.randbits(64))
        rng.shuffle(items)
        packet = []
        for i, it in enumerate(items):
            item_id = chr(ord("A") + i)
            packet.append({"item_id": item_id, "label": it["label"]})
            if it["kind"] == "target":
                trial["target_item_id"] = item_id  # kept server-side until ranking locks
        trial["packet"] = packet
        self._save_state()
        return {"code": code, "response": trial["response"], "items": packet}

    def submit_judgement(self, actor: str, code: str, ranking: list) -> dict:
        if actor.strip().lower() != self.protocol["judge"].strip().lower():
            raise MirrorError("Only the judge may submit a ranking.")
        code = str(code).strip()
        trial = self.state["trials"].get(code)
        if not trial or trial["status"] != "responded" or "packet" not in trial:
            raise MirrorError("Open the judge packet first, then rank.")
        valid_ids = [p["item_id"] for p in trial["packet"]]
        if sorted(ranking) != sorted(valid_ids):
            raise MirrorError("Ranking must list every item exactly once: " + ", ".join(valid_ids))
        secret = self._load_secret()[code]
        commitment_ok = sha256_text(
            secret["salt"] + canonical({"target": secret["target"], "decoys": secret["decoys"]})
        ) == trial["commitment"]
        if not commitment_ok:
            raise MirrorError("COMMITMENT MISMATCH — the sealed target was altered. Trial invalid.")
        hit = ranking[0] == trial["target_item_id"]
        trial["status"] = "judged"
        trial["ranking"] = ranking
        trial["hit"] = hit
        trial["revealed_target"] = secret["target"]
        self._save_state()
        self.ledger.append({"type": "trial_judged", "exp": self.exp_id, "code": code,
                            "hit": hit, "commitment_verified": True})
        return {"code": code, "hit": hit, "target": secret["target"]["label"]}

    # ---------- scoring / public view ----------

    def score(self) -> dict:
        trials = self.state["trials"]
        judged = [t for t in trials.values() if t["status"] == "judged"]
        hits = sum(1 for t in judged if t.get("hit"))
        n = len(judged)
        planned = self.protocol["n_trials"]
        return {
            "exp": self.exp_id,
            "title": self.protocol["title"],
            "subject": self.protocol["subject"],
            "sealed": len(trials),
            "responded": sum(1 for t in trials.values() if t["status"] in ("responded", "judged")),
            "judged": n,
            "hits": hits,
            "expected_by_chance": round(n * self.protocol["chance"], 2) if n else 0,
            "p_value": round(binomial_tail(n, hits, self.protocol["chance"]), 6) if n else None,
            "verdict": verdict_for(hits, n, planned, self.protocol["thresholds"]),
            "protocol_intact": self.check_protocol_integrity(),
            "ledger_intact": self.ledger.verify_chain(),
        }

    def public_export(self) -> dict:
        """Everything a skeptic needs to audit — except unrevealed secrets."""
        out_trials = {}
        for code, t in self.state["trials"].items():
            pub = {"status": t["status"], "commitment": t["commitment"]}
            if "response" in t:
                pub["response"] = t["response"]
                pub["response_hash"] = t["response_hash"]
            if t["status"] == "judged":
                pub["ranking"] = t["ranking"]
                pub["hit"] = t["hit"]
                pub["revealed_target"] = t["revealed_target"]
            out_trials[code] = pub
        return {"protocol": self.protocol, "score": self.score(), "trials": out_trials}
