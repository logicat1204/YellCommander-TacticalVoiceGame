import unittest

from yell.contract import UNITS, validate
from yell.live_commands import direct_order


class LiveCommandTests(unittest.TestCase):
    def test_in_game_phrases(self):
        for phrase, action, zone in (
            ("avancen hacia adelante a atacar", "atacar", "base_enemiga"),
            ("quiero que avancen y ataquen la base enemiga", "atacar", "base_enemiga"),
            ("vayan a destruir la base del enemigo", "atacar", "base_enemiga"),
            ("avancen hacia adelante", "avanzar", "base_enemiga"),
            ("vayan hasta la base contraria", "avanzar", "base_enemiga"),
            ("ataquen el flanco izquierdo", "atacar", "flanco_izquierdo"),
            ("protejan nuestra base", "defender", "base_aliada"),
            ("replieguense al centro", "retirarse", "centro"),
        ):
            with self.subTest(phrase=phrase):
                order = validate(direct_order("Alfa, " + phrase, UNITS))
                self.assertEqual((order["subject"]["name"], order["action"], order["location"]["id"]),
                                 ("Alfa", action, zone))

    def test_unresolved_or_ambiguous(self):
        for phrase in ("Alfa, no ataquen la base rival", "¿Alfa, ataquen?", "Bravo y Alfa ataquen",
                       "Alfa, defiendan nuestra base y ataquen el centro", "Zeta, ataquen la base enemiga",
                       "Alfa, ataquen cuando llegue Bravo", "Alfa, ataquen zona"):
            with self.subTest(phrase=phrase):
                self.assertIsNone(direct_order(phrase, UNITS))
