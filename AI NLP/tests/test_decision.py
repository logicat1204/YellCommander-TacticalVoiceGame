import unittest

from yell.decision import decide, resolve, wire
from yell.decision_data import build
from yell.service import active_aliases


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.people = {"Alfa-1":{"nombre":"Alex"}, "Alfa-2":{"nombre":"Juan"}}
        self.aliases = active_aliases(["Alfa"],list(self.people))
        for key,v in self.people.items():
            self.aliases[key].append(v["nombre"])

    def pick(self,text,action,here=None):
        return resolve(text,[(action,.99)],self.aliases,self.people,here)

    def test_soldier_squad_and_chat(self):
        for phrase,key in (("Alex, andá a cuidar el medio","Alfa-1"),
                           ("Alfa, que nadie pase por el medio","Alfa")):
            value,_ = decide(None,phrase,self.aliases,self.people)
            self.assertEqual(wire(value)["subject"]["name"],key)
            self.assertEqual(value["accion"],"defender")
        for text in ("Alex, ¿defendés el centro?", "Juan, no defiendas el centro",
                     "Alex y Juan defiendan el centro","Alex, defendé","Pedro, defendé el centro"):
            self.assertEqual(self.pick(text,"defender")["tipo"],"charla")
        self.assertEqual(self.pick("Juan, quedate acá","mantener_posicion","centro")["lugar"],"centro")
        self.assertEqual(self.pick("Alex, curalo a Juan en el centro","curar")["objetivo"]["id"],"Alfa-2")

    def test_splits(self):
        seen = set()
        for rows in build().values():
            families = {r["family"] for r in rows}
            self.assertFalse(seen & families)
            seen.update(families)
            for row in rows:
                if row["label"] != "charla":
                    self.assertEqual(self.pick_row(row)["tipo"],"accion",row["text"])

    def pick_row(self,r):
        return resolve(r["text"],[(r["label"],.99)],r["aliases"],r["roster"],r["here"])

