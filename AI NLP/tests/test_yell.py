import base64
import io
import json
import unittest
import wave

from yell.contract import SCHEMA, UNITS, check_grounding, command, matches, tokens, validate
from yell.data import audit, corpus
from yell.inference import decoding_schema, infer
from yell.service import active_aliases, check_live_agreement, wav_input


class ContractTests(unittest.TestCase):
    def test_span_normalization_and_longest_alias(self):
        self.assertEqual(tokens("¡MÉDICOS, atiendan a Chárli!"), ["medicos", "atiendan", "a", "charli"])
        self.assertEqual(matches("¡Equipo médico, a Bravo!", UNITS),
                         [(0, 2, "Médico"), (3, 4, "Bravo")])

    def test_strict_contract(self):
        proposal = command("orden", "Alfa", "avanzar", "centro")
        self.assertEqual(validate(json.loads(json.dumps(proposal))), proposal)
        for change in ({"version": True}, {"version": 2}, {"action": "saludar"}, {"meta": 1},
                       {"model_confidence": float("nan")}, {"location": {"id": "ninguna"}},
                       {"target": {"type": "peloton", "name": "Bravo"}}, {"intent": "chat"},
                       {"subject": {"type": "peloton", "name": " "}}, {"intent": "charla"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate({**proposal, **change})

    def test_schema_equivalence_on_valid_examples(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema no instalado")
        schema = Draft202012Validator(SCHEMA)
        for records in corpus().values():
            for example in records:
                schema.validate(example["label"])

    def test_llm_schema_restricts_entities_and_medical_fields(self):
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.skipTest("jsonschema no instalado")
        schema = Draft202012Validator(decoding_schema("Médicos, atiendan a Bravo en el centro", UNITS))
        self.assertTrue(schema.is_valid(command("orden", "Médico", "curar", "centro", "Bravo")))
        self.assertFalse(schema.is_valid(command("orden", "Médico", "avanzar", "centro", "Bravo")))
        self.assertFalse(schema.is_valid(command("orden", "Médico", "curar", "base_enemiga", "Bravo")))

    def test_negation_and_compound_cannot_execute(self):
        proposal = command("orden", "Alfa", "avanzar", "centro")
        for utterance in ("Alfa no avancen al centro", "Alfa, avancen al centro y retrocedan",
                          "Alfa, avancen al centro si oyen algo", "¿Alfa, avanzaron al centro?"):
            validated, why = check_grounding(utterance, proposal, UNITS)
            self.assertEqual(validated, command())
            self.assertTrue(why)

    def test_grounded_medical_order_and_custom_alias(self):
        proposal = command("orden", "Médico", "curar", "centro", "Bravo")
        self.assertEqual(check_grounding("Médicos, curen a Bravo en el centro", proposal, UNITS), (proposal, ""))
        self.assertEqual(check_grounding("Médicos, curen a Alfa en el centro", proposal, UNITS)[0], command())
        proposal = command("orden", "Cobalto", "avanzar", "centro")
        self.assertEqual(check_grounding("¡Cobalto, al centro!", proposal, active_aliases(["Cobalto"])), (proposal, ""))
        soldier = command("orden", "Alfa-2", "avanzar", "centro")
        self.assertEqual(soldier["subject"]["type"], "soldado")
        self.assertEqual(check_grounding("Soldado Alfa dos, avancen al centro", soldier,
                                         active_aliases(["Alfa"], ["Alfa-2"])), (soldier, ""))

    def test_low_confidence_abstention(self):
        class Predictor:
            def predict(self, text, aliases):
                return command("orden", "Alfa", "avanzar", "centro", confidence=0.34)

        raw, executed, reason, latency = infer(Predictor(), "Alfa, avancen al centro")
        self.assertEqual(raw["action"], "avanzar")
        self.assertEqual(executed, command())
        self.assertTrue(reason)
        self.assertGreaterEqual(latency, 0)

    def test_live_agreement_compares_semantics(self):
        qwen = command("orden", "Bravo", "defender", "centro")
        self.assertTrue(check_live_agreement(qwen, {**qwen, "model_confidence": 0.9}))
        self.assertFalse(check_live_agreement(qwen, {**qwen, "action": "atacar"}))
        self.assertFalse(check_live_agreement(qwen, None))
        self.assertTrue(check_live_agreement(command("charla"), None))


class DataTests(unittest.TestCase):
    def test_disjoint_families_and_normalized_phrases(self):
        data = corpus()
        families, phrases = set(), set()
        for split, items in data.items():
            with self.subTest(split=split):
                own_families = {r["family"] for r in items}
                own_phrases = {tuple(tokens(r["text"])) for r in items}
                self.assertFalse(families & own_families)
                self.assertFalse(phrases & own_phrases)
                self.assertEqual(len(own_phrases), len(items))
                self.assertEqual({r["label"]["intent"] for r in items}, {"orden", "motivacion", "charla", "desconocido"})
                self.assertTrue(all(len(r["bio"]) == len(tokens(r["text"])) for r in items))
                families.update(own_families)
                phrases.update(own_phrases)
        self.assertEqual(sum(audit()[k]["rows"] for k in data), 1510)

    def test_wav_transport_checks_format_and_truncation(self):
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            output.writeframes(b"\x00" * 16000)
        audio = buffer.getvalue()
        self.assertEqual(wav_input(base64.b64encode(audio).decode()), audio)
        for bad in ("invalid!!", base64.b64encode(audio[:-10]).decode()):
            with self.assertRaises(ValueError):
                wav_input(bad)


if __name__ == "__main__":
    unittest.main()
