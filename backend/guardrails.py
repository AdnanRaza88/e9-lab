class GuardrailError(Exception):
    pass


def input_guardrail(report_text, criteria):
    if len(report_text) < 200:
        raise GuardrailError("report below minimum length")


def output_guardrail(scores):
    for s in scores:
        if not s.evidence_quote or len(s.evidence_quote) < 10:
            raise GuardrailError(f"missing evidence quote for {s.name}")
