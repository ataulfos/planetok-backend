"""AI agent module — stub. The ``feat/ai`` subagent implements this.

Contract the agent MUST expose (consumed by features/tasks):

    def analyze_task(title: str, description: str) -> dict:
        '''
        Returns:
            {
                "category": "personal" | "work" | "urgent",
                "subtasks": ["step 1", "step 2", ...]
            }
        Raises:
            AIAgentError on LLM failure / invalid output.
        '''
"""


class AIAgentError(Exception):
    """Raised when the LLM is unavailable or returns invalid output."""


def analyze_task(title: str, description: str) -> dict:
    raise AIAgentError("ai agent not implemented yet")
