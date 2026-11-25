import unittest
from types import SimpleNamespace

from yell.contract import UNITS
from yell.service import clarify_speech, prefer_retry, retry_reason


def voice(text, quality=-.3):
    return SimpleNamespace(status="voz", text=text, min_logprob=quality)


class RetryPolicyTests(unittest.TestCase):
    def test_route_clear_audio_without_second_pass(self):
        chat = ({"tipo": "charla"}, [("charla", .99)], "clasificador")
        order = ({"tipo": "accion"}, [("avanzar", .96)], "clasificador")
        for text, parsed in (("Bravo como estas", chat), ("Alfa, ¿cuánta salud tienes?", chat),
                             ("Necesito a Bravo en el centro", order)):
            self.assertEqual(retry_reason(voice(text), parsed, UNITS, None), "")
        self.assertEqual(retry_reason(voice("Bravo defiendan"), chat, UNITS, None), "orden_posiblemente_incompleta")
        self.assertEqual(retry_reason(voice("Bravo al centro", -.88), order, UNITS, None), "calidad_acustica")

    def test_retry_respects_locations_including_here_and_qualifiers(self):
        self.assertTrue(prefer_retry(voice("Alfa aquí en la base de la mía"),
                                     voice("Alfa ataque en la base enemiga"), UNITS, "centro"))
        for before, after in (("Alfa, quédense acá", "Alfa vayan a la derecha"),
                              ("Alfa nunca vayan", "Alfa vayan al centro"),
                              ("Bravo en nuestra base", "Bravo a la base rival")):
            self.assertFalse(prefer_retry(voice(before), voice(after), UNITS, "centro"))

    def test_uncertain_order_requests_clarification(self):
        info = {"retried": True, "used_retry": False, "retry_reason": "destino_incierto"}
        self.assertTrue(clarify_speech(info, {"tipo":"accion"}, [("atacar", .99)], "Alfa, atacá la base de Miga"))
        self.assertFalse(clarify_speech(info, {"tipo":"accion"}, [("atacar", .99)], "Alfa, atacá la base enemiga"))
