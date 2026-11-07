import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mirror.core import Experiment, MirrorError, binomial_tail, verdict_for  # noqa: E402

FRAGS = {
    "shape": "long, narrow, wider at one end",
    "material": "wood",
    "color": "light brown",
    "texture": "smooth, grain visible",
    "size": "about a hand and a half",
    "natural_or_made": "made, from a natural material",
    "function_sense": "holding / serving something",
    "unusual_detail": "holes cut through the handle end",
    "not_statement": "it is NOT metal",
    "name_guess": "wooden salad spoon",
}


class MirrorTest(unittest.TestCase):
    def setUp(self):
        self.data = tempfile.mkdtemp(prefix="mirror-test-")
        self.exp = Experiment.create(self.data, "Block 1", "Automator", "Jordan", "Ryan", "Mom")

    def tearDown(self):
        shutil.rmtree(self.data, ignore_errors=True)

    def seal(self, code="481516", target="wooden salad spoon"):
        return self.exp.seal_trial("Jordan", code, {"label": target, "kind": "object"},
                                   [{"label": "metal fork"}, {"label": "plastic cup"},
                                    {"label": "wooden ruler"}])

    def respond(self, code="481516"):
        return self.exp.submit_response("Automator", code, dict(FRAGS), 70)

    # --- roles & freezing ---
    def test_roles_must_be_distinct(self):
        with self.assertRaises(MirrorError):
            Experiment.create(self.data, "Bad", "Same", "Same", "Ryan", "Mom")
        with self.assertRaises(MirrorError):
            Experiment.create(self.data, "Bad2", "Subj", "Targ", "Targ", "Judge")

    def test_protocol_hash_intact_and_tamper_detected(self):
        self.assertTrue(self.exp.check_protocol_integrity())
        self.exp.protocol["title"] = "edited after the fact"
        self.assertFalse(self.exp.check_protocol_integrity())

    def test_only_targeter_seals(self):
        with self.assertRaises(MirrorError):
            self.exp.seal_trial("Ryan", "481516", {"label": "x"}, [{"label": "a"}] * 3)

    def test_code_must_be_six_digits(self):
        with self.assertRaises(MirrorError):
            self.seal(code="123")

    # --- response locking ---
    def test_response_locks_and_cannot_redo(self):
        self.seal()
        self.respond()
        with self.assertRaises(MirrorError):
            self.respond()

    def test_response_requires_all_fragments(self):
        self.seal()
        bad = dict(FRAGS)
        bad["unusual_detail"] = ""
        with self.assertRaises(MirrorError):
            self.exp.submit_response("Automator", "481516", bad, 50)

    def test_response_before_seal_rejected(self):
        with self.assertRaises(MirrorError):
            self.respond(code="999999")

    # --- blind judging ---
    def test_packet_does_not_leak_target(self):
        self.seal()
        self.respond()
        pkt = self.exp.judge_packet("Mom", "481516")
        self.assertEqual(len(pkt["items"]), 4)
        for item in pkt["items"]:
            self.assertEqual(set(item.keys()), {"item_id", "label"})

    def test_judge_must_rank_every_item_once(self):
        self.seal()
        self.respond()
        pkt = self.exp.judge_packet("Mom", "481516")
        ids = [i["item_id"] for i in pkt["items"]]
        with self.assertRaises(MirrorError):
            self.exp.submit_judgement("Mom", "481516", ids[:3])

    def test_hit_scoring_and_reveal(self):
        self.seal()
        self.respond()
        pkt = self.exp.judge_packet("Mom", "481516")
        # find the target's item id from state (test-only peek at server side)
        target_id = self.exp.state["trials"]["481516"]["target_item_id"]
        others = [i["item_id"] for i in pkt["items"] if i["item_id"] != target_id]
        result = self.exp.submit_judgement("Mom", "481516", [target_id] + others)
        self.assertTrue(result["hit"])
        self.assertEqual(result["target"], "wooden salad spoon")
        s = self.exp.score()
        self.assertEqual(s["hits"], 1)
        self.assertEqual(s["judged"], 1)

    def test_targeter_cannot_judge(self):
        self.seal()
        self.respond()
        with self.assertRaises(MirrorError):
            self.exp.judge_packet("Jordan", "481516")

    # --- ledger ---
    def test_ledger_chain_verifies_and_tamper_breaks_it(self):
        self.seal()
        self.respond()
        self.assertTrue(self.exp.ledger.verify_chain())
        self.exp.ledger.entries[0]["type"] = "forged"
        self.assertFalse(self.exp.ledger.verify_chain())

    def test_public_export_hides_unrevealed_target(self):
        self.seal()
        pub = self.exp.public_export()
        self.assertNotIn("revealed_target", pub["trials"]["481516"])
        self.assertNotIn("wooden salad spoon", str(pub["trials"]))

    # --- statistics ---
    def test_binomial_tail_known_values(self):
        self.assertAlmostEqual(binomial_tail(24, 24), 0.25 ** 24, places=12)
        self.assertAlmostEqual(binomial_tail(24, 0), 1.0)
        # chance-level performance (6/24) must NOT look significant
        self.assertGreater(binomial_tail(24, 6), 0.4)
        # 16/24 must be very significant
        self.assertLess(binomial_tail(24, 16), 0.001)

    def test_verdict_thresholds(self):
        self.assertIn("NOT PROVEN", verdict_for(10, 24, 24))
        self.assertIn("WORTH REPLICATING", verdict_for(11, 24, 24))
        self.assertIn("STRONG", verdict_for(12, 24, 24))
        self.assertIn("EXTRAORDINARY", verdict_for(16, 24, 24))
        self.assertIn("provisional", verdict_for(16, 12, 24))

    # --- end to end ---
    def test_full_block_perfect_subject_scores_extraordinary(self):
        exp = Experiment.create(self.data, "Full", "Automator", "Jordan", "Ryan", "Mom")
        for i in range(24):
            code = f"{100000 + i}"
            exp.seal_trial("Jordan", code, {"label": f"target-{i}", "kind": "object"},
                           [{"label": f"decoy-{i}-a"}, {"label": f"decoy-{i}-b"},
                            {"label": f"decoy-{i}-c"}])
            exp.submit_response("Automator", code, dict(FRAGS), 80)
            pkt = exp.judge_packet("Mom", code)
            target_id = exp.state["trials"][code]["target_item_id"]
            others = [x["item_id"] for x in pkt["items"] if x["item_id"] != target_id]
            exp.submit_judgement("Mom", code, [target_id] + others)
        s = exp.score()
        self.assertEqual(s["hits"], 24)
        self.assertIn("EXTRAORDINARY", s["verdict"])
        self.assertTrue(s["ledger_intact"])
        self.assertTrue(s["protocol_intact"])

    def test_full_block_chance_judge_is_not_proven(self):
        import random
        rng = random.Random(42)
        exp = Experiment.create(self.data, "Chance", "Automator", "Jordan", "Ryan", "Mom")
        for i in range(24):
            code = f"{200000 + i}"
            exp.seal_trial("Jordan", code, {"label": f"t-{i}", "kind": "object"},
                           [{"label": f"d-{i}-a"}, {"label": f"d-{i}-b"}, {"label": f"d-{i}-c"}])
            exp.submit_response("Automator", code, dict(FRAGS), 50)
            pkt = exp.judge_packet("Mom", code)
            ids = [x["item_id"] for x in pkt["items"]]
            rng.shuffle(ids)
            exp.submit_judgement("Mom", code, ids)
        s = exp.score()
        # a seeded random judge should land near chance, nowhere near strong
        self.assertLess(s["hits"], 12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
