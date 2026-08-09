import structlog

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()


def log_specialist_call(agent_call_id, criterion_name, model, output, latency_ms):
    logger.info(
        "specialist_call",
        agent_call_id=agent_call_id,
        criterion=criterion_name,
        model=model,
        output=output,
        latency_ms=latency_ms
    )
