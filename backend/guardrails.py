class GuardrailError(Exception):
    pass


def input_guardrail(report_text, criteria):
    if len(report_text) < 200:
        raise GuardrailError("report below minimum length")
    total_weight = sum(c["weight"] for c in criteria)
    if abs(total_weight - 100) > 0.01:
        raise GuardrailError("rubric weights do not sum to 100")


def output_guardrail(scores):
    for s in scores:
        if not s.evidence_quote or len(s.evidence_quote) < 10:
            raise GuardrailError(f"missing evidence quote for {s.name}")
