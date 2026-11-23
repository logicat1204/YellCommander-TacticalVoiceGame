import io
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np

from yell.inference import SpeechToText
from yell.contract import UNITS, command
from yell.service import Service, prefer_retry
from yell.live_commands import repair_spoken_order


def fixture(level=0.1, rate=48000):
    samples = np.full(rate // 2, round(level * 32767), dtype="<i2")
    result = io.BytesIO()
    with wave.open(result, "wb") as stream:
        stream.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(samples.tobytes())
    return result.getvalue()


class SpeechTests(unittest.TestCase):
    def test_qwen_proposal_can_be_verified_by_second_model(self):
        server = Service.__new__(Service)
        server.models = {"A": Mock(), "B": Mock()}
        server.threshold = 0.70
        server.verifier = Mock()
        server.models["A"].predict.return_value = command()
        proposal = command("motivacion")
        server.models["B"].predict.return_value = proposal
        server.verifier.predict.return_value = proposal
        phrase = "Muchachos, podemos lograrlo"
        _, result, _, _, verifier = server.interpret("B", phrase, UNITS, list(UNITS), False)
        self.assertEqual((result["intent"], verifier), ("motivacion", "C"))
        server.verifier.predict.return_value = command("charla")
        self.assertEqual(server.interpret("B", phrase, UNITS, list(UNITS), False)[1]["intent"], "desconocido")

    def test_underspecified_defense_and_explicit_negation(self):
        server = Service.__new__(Service)
        for text, route in (("Bravo defiendan", "aclaracion"), ("Alfa, no ataquen al centro", "negacion")):
            _, order, reason, observed, _ = server.interpret("B", text, UNITS, list(UNITS), False)
            self.assertEqual((order["intent"], observed), ("desconocido", route))
            self.assertTrue(reason)

    def test_retry_keeps_negation_recipient_and_location(self):
        def spoken(text):
            return SimpleNamespace(status="voz", text=text)
        for first, retry in (("Alfa no vayan", "Alfa vayan"), ("Bravo al centro", "Alfa al centro"),
                             ("Bravo por el flanco izquierdo", "Bravo por el flanco derecho")):
            self.assertFalse(prefer_retry(spoken(first), spoken(retry), UNITS))
        self.assertTrue(prefer_retry(spoken("Labo al centro"), spoken("Bravo al centro"), UNITS))

    def test_recover_callsign_only_in_complete_spoken_order(self):
        for variant in ("Drabo", "Trabo", "Rabo", "Brabo"):
            result = repair_spoken_order(variant + ", avancen hacia el centro", UNITS, ["Bravo"])
            self.assertEqual(result["subject"]["name"], "Bravo")
        self.assertIsNone(repair_spoken_order("Rabo, no avancen al centro", UNITS, ["Bravo"]))
        self.assertIsNone(repair_spoken_order("Rabo, avancen al centro", UNITS, ["Alfa"]))
        self.assertIsNone(repair_spoken_order("Bravo hasta que en la base", UNITS, ["Bravo"]))

    def setUp(self):
        self.speech = SpeechToText.__new__(SpeechToText)
        self.speech.model = Mock()

    def reply(self, text="Alfa, avancen al centro", probability=-0.2, kept=0.4, compression=1.0):
        return ([SimpleNamespace(text=text, avg_logprob=probability, no_speech_prob=0.1,
                                 compression_ratio=compression)], SimpleNamespace(duration_after_vad=kept))

    def test_silence_does_not_start_whisper(self):
        result = self.speech.recognize(fixture(level=0))
        self.assertEqual(result.status, "sin_senal")
        self.assertEqual(result.audio_ms, 500)
        self.speech.model.transcribe.assert_not_called()

    def test_vad_rejection_clears_even_a_plausible_transcript(self):
        self.speech.model.transcribe.return_value = self.reply(kept=0.03)
        result = self.speech.recognize(fixture())
        self.assertEqual((result.status, result.text, result.speech_ms), ("sin_voz", "", 30.0))

    def test_confidence_and_repetition_reject_the_entire_fragment(self):
        for reply in (self.reply(probability=-1.20), self.reply(compression=3.0)):
            self.speech.model.transcribe.return_value = reply
            result = self.speech.recognize(fixture())
            self.assertEqual((result.status, result.text), ("transcripcion_incierta", ""))

    def test_decodes_valid_audio_in_spanish_and_keeps_negation(self):
        text = "Alfa, no avancen al centro"
        self.speech.model.transcribe.return_value = self.reply(text=text)
        result = self.speech.recognize(fixture())
        self.assertEqual((result.status, result.text), ("voz", text))
        pcm = self.speech.model.transcribe.call_args.args[0]
        self.assertEqual(len(pcm), 8000)
        kwargs = self.speech.model.transcribe.call_args.kwargs
        self.assertEqual(kwargs["language"], "es")
        self.assertTrue(kwargs["vad_filter"])


if __name__ == "__main__":
    unittest.main()
