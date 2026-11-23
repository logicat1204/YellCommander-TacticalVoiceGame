from collections import Counter
from statistics import median, quantiles

from .contract import INTENTS


def semantic(label):
    return tuple(label[key] for key in ("intent", "subject", "action", "location", "target"))


def classification(actual, predicted, names):
    matrix = Counter(zip(actual, predicted))
    scores = {}
    for label in names:
        score = matrix[label, label]
        support = actual.count(label)
        guessed = predicted.count(label)
        precision = score / max(guessed, 1)
        recall = score / max(support, 1)
        scores[str(label)] = {"precision": precision, "recall": recall, "support": support,
                              "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0}
    return {"accuracy": sum(a == b for a, b in zip(actual, predicted)) / max(len(actual), 1),
            "macro_f1": sum(row["f1"] for row in scores.values()) / len(scores),
            "labels": scores, "confusion": [[matrix[a, b] for b in names] for a in names]}


def summary(expected, predicted, times=()):
    count = len(expected)
    orders = [(a, b) for a, b in zip(expected, predicted) if a["intent"] == "orden"]
    abstentions = [(a, b) for a, b in zip(expected, predicted) if a["intent"] == "desconocido"]
    fields = ("subject", "action", "location", "target")
    spans_a = {(i, key, str(row[key])) for i, row in enumerate(expected)
               for key in ("subject", "location", "target") if row[key] is not None}
    spans_b = {(i, key, str(row[key])) for i, row in enumerate(predicted)
               for key in ("subject", "location", "target") if row[key] is not None}
    entity_f1 = 2 * len(spans_a & spans_b) / max(len(spans_a) + len(spans_b), 1)
    result = {
        "samples": count, "intent": classification([x["intent"] for x in expected],
                                                     [x["intent"] for x in predicted], INTENTS),
        "exact_match": sum(semantic(a) == semantic(b) for a, b in zip(expected, predicted)) / count,
        "order_exact_match": sum(semantic(a) == semantic(b) for a, b in orders) / max(len(orders), 1),
        "order_field_accuracy": {key: sum(a[key] == b[key] for a, b in orders) / max(len(orders), 1) for key in fields},
        "normalized_entity_f1": entity_f1,
        "ood_correct_abstention": sum(b["intent"] == "desconocido" for _, b in abstentions) / max(len(abstentions), 1),
        "incorrect_order_proposal_rate": sum(b["intent"] == "orden" and semantic(a) != semantic(b)
                                            for a, b in zip(expected, predicted)) / count,
    }
    if len(times) > 1:
        result.update(median_ms=median(times), p95_ms=quantiles(times, n=100, method="inclusive")[94])
    return result
