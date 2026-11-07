import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mirror.core import MirrorError  # noqa: E402
from mirror.solo import (ATTRIBUTES, POOL_SIZE, VOCAB, SoloBlock,  # noqa: E402
                         prototype_subject, random_subject,
                         run_block_with_subject, score_candidate)


class SoloTest(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="mirror-solo-")

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)

    def test_pool_is_huge(self):
        # 10*10*12*8*7*3*12 — no "typical object" strategy can cover this
        self.assertEqual(POOL_SIZE, 2419200)

    def test_draws_are_recomputable_from_beacon_and_salt(self):
        blk = SoloBlock.create(self.data, "audit", n_trials=4, beacon="beacon-X")
        salt = None
        import json as _json
        with open(os.path.join(blk.dir, "solo_secret.json")) as f:
            secret = _json.load(f)
        salt = secret["salt"]
        from mirror.solo import derive_rng, draw_combo
        rng = derive_rng("beacon-X", salt, 0)
        first_target = draw_combo(rng)
        code0 = list(blk.block["trials"].keys())[0]
        self.assertEqual(secret["trials"][code0]["target"], first_target)

    def test_response_must_use_vocabulary(self):
        blk = SoloBlock.create(self.data, "s", n_trials=1)
        code = list(blk.block["trials"].keys())[0]
        bad = {a: VOCAB[a][0] for a in ATTRIBUTES}
        bad["material"] = "unobtainium"
        with self.assertRaises(MirrorError):
            blk.run_trial(code, bad)

    def test_response_locks(self):
        blk = SoloBlock.create(self.data, "s", n_trials=1)
        code = list(blk.block["trials"].keys())[0]
        resp = {a: VOCAB[a][0] for a in ATTRIBUTES}
        blk.run_trial(code, dict(resp))
        with self.assertRaises(MirrorError):
            blk.run_trial(code, dict(resp))

    def test_salt_reveal_blocked_until_complete(self):
        blk = SoloBlock.create(self.data, "s", n_trials=2)
        with self.assertRaises(MirrorError):
            blk.reveal_salt()

    def test_oracle_subject_scores_perfect(self):
        # A subject that (in this test only) is handed the targets MUST score
        # ~100% — otherwise the scorer could never detect a real signal.
        import json as _json
        blk = SoloBlock.create(self.data, "oracle", n_trials=48, beacon="oracle-seed")
        with open(os.path.join(blk.dir, "solo_secret.json")) as f:
            secret = _json.load(f)["trials"]

        def oracle(code):
            return dict(secret[code]["target"])

        s = run_block_with_subject(blk, oracle)
        self.assertEqual(s["hits"], 48)
        self.assertLess(s["p_value"], 1e-20)
        self.assertIn("EXTRAORDINARY", s["verdict"])

    def test_random_subject_lands_at_chance_1000(self):
        blk = SoloBlock.create(self.data, "random-control", n_trials=1000,
                               beacon="validation-seed-1")
        s = run_block_with_subject(blk, random_subject(7))
        # chance = 250, sd ≈ 13.7 — a rig that pushed this outside ±60 would
        # be broken; and its verdict must be NOT PROVEN.
        self.assertTrue(190 <= s["hits"] <= 310, f"random hits={s['hits']}")
        self.assertEqual(s["verdict"], "NOT PROVEN")
        self.assertTrue(s["ledger_intact"])

    def test_prototype_subject_lands_at_chance_1000(self):
        blk = SoloBlock.create(self.data, "prototype-control", n_trials=1000,
                               beacon="validation-seed-2")
        s = run_block_with_subject(blk, prototype_subject())
        self.assertTrue(190 <= s["hits"] <= 310, f"prototype hits={s['hits']}")
        self.assertEqual(s["verdict"], "NOT PROVEN")

    def test_score_candidate_weights(self):
        resp = {a: VOCAB[a][0] for a in ATTRIBUTES}
        self.assertEqual(score_candidate(resp, dict(resp)), 15)  # 3+3+2+2+1+1+3
        other = {a: VOCAB[a][1] for a in ATTRIBUTES}
        self.assertEqual(score_candidate(resp, other), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
