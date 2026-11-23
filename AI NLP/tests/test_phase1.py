import unittest

from yell.contract import ACTIONS, ROOT, UNITS, check_grounding, command
from yell.data import corpus
from yell.evaluate import calibration, evaluate_text
from yell.phase1_data import audit_phase1, build_phase1


class Phase1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.splits = build_phase1()

    def test_historical_holdout_and_group_isolation(self):
        self.assertEqual(self.splits["test_v1"], corpus()["test"])
        audit = audit_phase1(self.splits)
        for label in ("train", "val", "test_v1", "test_v2"):
            self.assertEqual(set(audit[label]["actions"]), set(ACTIONS[1:]))
            self.assertEqual(len(audit[label]["intents"]), 4)
        self.assertGreater(len(self.splits["train"]), 2000)

    def test_negated_or_compound_instructions_abstain(self):
        candidate = command("orden", "Alfa", "avanzar", "centro")
        for sentence in ("Alfa, no se acerquen al centro.", "Alfa, avancen y defiendan el centro.",
                         "Alfa, vayan al centro; después cancela."):
            decision, reason = check_grounding(sentence, candidate, UNITS)
            self.assertEqual(decision["intent"], "desconocido")
            self.assertTrue(reason)

    def test_calibration_uses_intent_and_action_jointly(self):
        gold = [command("orden", "Alfa", "avanzar", "centro")]
        score = calibration(gold, [command("orden", "Alfa", "defender", "centro", confidence=0.8)])
        self.assertAlmostEqual(score["ece"], 0.8)
        self.assertAlmostEqual(score["brier"], 0.64)
        self.assertIsNone(calibration(gold, gold))

    def test_trained_checkpoint_round_trip(self):
        if not (ROOT / "models" / "transfer-c" / "training.json").is_file():
            self.skipTest("Entrene el Modelo C para ejecutar la prueba de integración")
        from yell.evaluate import get_model

        model = get_model("C")
        accepted = evaluate_text(model, "Alfa, avancen por el centro")["command"]
        self.assertEqual((accepted["intent"], accepted["action"], accepted["location"]["id"]),
                         ("orden", "avanzar", "centro"))
        denied = evaluate_text(model, "Alfa, no avancen por el centro")["command"]
        self.assertNotEqual(denied["action"], "avanzar")


if __name__ == "__main__":
    unittest.main()
