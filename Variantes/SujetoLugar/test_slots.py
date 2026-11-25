import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "AI NLP"))
from slots import SlotClassifier


class SlotsTest(unittest.TestCase):
    def test_known_actions_and_boundaries(self):
        aliases = {"Alfa":["alfa"], "Bravo":["bravo"], "Alfa-1":["Tomás"]}
        roster = {"Alfa-1":{"nombre":"Tomás"}}
        for posture in (False, True):
            classifier = SlotClassifier(posture)
            for text, person, destination in (
                ("Tomás, avancen por el centro", "Alfa-1", "centro"),
                ("Alfa, ataquen la base enemiga", "Alfa", "base_enemiga"),
                ("Bravo, defiendan nuestra base", "Bravo", "base_aliada"),
                ("Alfa y Bravo, vayan al centro", None, None),
                ("Tomasi, Bravo, vaya al centro", None, None),
                ("Bravo, ¿cómo va todo por el centro?", None, None),
                ("Bravo, no se muevan del centro", None, None),
                ("Tomás, en caso de que llueva luego andá al centro", None, None),
                ("Alfa, avancen", None, None),
                ("Tomás, curen a Bravo en el centro", None, None),
                ("Alfa, cancelen la orden en el centro", None, None)):
                result, _, _ = classifier.classify(None, text, aliases, roster, "centro", True)
                self.assertEqual((result.get("sujeto",{}).get("id"), result.get("lugar")), (person, destination), text)
                if destination == "base_aliada":
                    self.assertEqual(result["accion"], "defender" if posture else "avanzar")


if __name__ == "__main__":
    unittest.main()
