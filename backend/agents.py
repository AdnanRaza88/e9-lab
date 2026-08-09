import asyncio
import json
import time
from groq import AsyncGroq

from models import CriterionScore, ExportJSON, ExportMetadata, ExportScoreEntry
from logger import log_specialist_call

client = AsyncGroq()

MODEL = "llama-3.3-70b-versatile"


def build_tools(criteria):
    tools = []
    for c in criteria:
        tool_name = f"score_{c['name'].lower().replace(' ', '_')}"
        tools.append({
            "type": "function",
            "function": {
                "name": tool_name,
                "description": c["description"],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_text": {"type": "string"}
                    },
                    "required": ["report_text"]
                }
            }
        })
    return tools


async def run_specialist(agent_call_id, criterion_name, criterion_description, report_text):
    start = time.monotonic()
    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You score lab reports on a single criterion: '{criterion_name}'. "
                    f"Criterion definition: {criterion_description}. "
                    "Respond only with JSON containing score (0-100), evidence_quote "
                    "(a direct quote copied from the report), improvement_note, and confidence (0-1)."
                )
            },
            {"role": "user", "content": report_text}
        ],
        response_format={"type": "json_object"}
    )
    raw_output = response.choices[0].message.content
    latency_ms = round((time.monotonic() - start) * 1000, 2)
    log_specialist_call(agent_call_id, criterion_name, MODEL, raw_output, latency_ms)

    parsed = json.loads(raw_output)
    return CriterionScore(
        name=criterion_name,
        score=parsed["score"],
        evidence_quote=parsed["evidence_quote"],
        improvement_note=parsed["improvement_note"],
        confidence=parsed["confidence"]
    )


async def run_orchestrator(criteria, report_text, report_id):
    tools = build_tools(criteria)
    orchestrator_response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "Call every scoring tool provided exactly once, passing the full report text to each."
            },
            {"role": "user", "content": report_text}
        ],
        tools=tools,
        tool_choice="required"
    )

    calls = orchestrator_response.choices[0].message.tool_calls
    tasks = []
    for index, call in enumerate(calls):
        criterion = next(
            c for c in criteria
            if call.function.name.endswith(c["name"].lower().replace(" ", "_"))
        )
        agent_call_id = f"{report_id}_{index}"
        tasks.append(run_specialist(agent_call_id, criterion["name"], criterion["description"], report_text))

    return await asyncio.gather(*tasks)


async def json_export_agent(scorecard, criteria):
    weight_map = {c["name"]: c["weight"] for c in criteria}

    scores_array = [
        ExportScoreEntry(
            criterion=s["name"],
            score=s["score"],
            weight=weight_map.get(s["name"], 0)
        )
        for s in scorecard.raw_scores
    ]

    export = ExportJSON(
        metadata=ExportMetadata(
            report_id=scorecard.report_id,
            rubric_id=scorecard.rubric_id,
            exported_at=scorecard.created_at
        ),
        scores_array=scores_array,
        total_grade=scorecard.grade,
        total_percentage=scorecard.weighted_total,
        raw_quotes={s["name"]: s["evidence_quote"] for s in scorecard.raw_scores}
    )

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Validate the given export JSON structure and return it back as valid JSON "
                    "with the exact same keys and values, unchanged."
                )
            },
            {"role": "user", "content": export.model_dump_json()}
        ],
        response_format={"type": "json_object"}
    )

    try:
        validated = json.loads(response.choices[0].message.content)
        return ExportJSON(**validated)
    except Exception:
        return export
