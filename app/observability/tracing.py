"""Agent execution tracing.

Wraps each LangGraph node with timing instrumentation so per-agent
execution time is captured on every workflow run. Durations are
appended to ``state["timings"]`` and surfaced to clients via
``SummaryResponse.timings``.
"""

from time import perf_counter
from typing import Any, Callable

NodeFn = Callable[[dict[str, Any]], dict[str, Any]]


def timed_node(name: str, fn: NodeFn) -> NodeFn:
    """Wrap a LangGraph node function so its execution time is recorded.

    Args:
        name: Agent name reported in ``AgentTiming`` (also the LangGraph
            node name).
        fn: The agent function to time. Receives and partially updates
            the workflow state.
    """

    def node(state: dict[str, Any]) -> dict[str, Any]:
        started = perf_counter()
        result = fn(state)
        timing = {"agent": name, "duration_ms": round((perf_counter() - started) * 1000, 2)}
        return {**result, "timings": [*state.get("timings", []), timing]}

    return node
