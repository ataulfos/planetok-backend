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
    from app.core.config import settings

    if not settings.OPENAI_API_KEY:
        raise AIAgentError("missing OPENAI_API_KEY")

    try:
        from langchain_openai import ChatOpenAI
    except Exception as e:  # pragma: no cover
        raise AIAgentError(f"langchain-openai unavailable: {e}")

    llm = ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=0.2,
        timeout=20,
    )

    system = (
        "You are a task analysis assistant.\n"
        "Given a task title and description, you must return ONLY valid JSON.\n"
        'Schema: {"category":"personal|work|urgent","subtasks":["...", "..."]}\n'
        "- category must be exactly one of: personal, work, urgent.\n"
        "- subtasks must be 2 to 6 short, actionable steps.\n"
        "- Do not include any extra keys.\n"
        "- Do not wrap JSON in markdown.\n"
    )
    user = f"Title: {title}\nDescription: {description or ''}"

    try:
        msg = llm.invoke(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        )
    except Exception as e:
        raise AIAgentError(str(e))

    content = getattr(msg, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise AIAgentError("empty model response")

    import json

    try:
        data = json.loads(content)
    except Exception:
        # Some models may include stray text; try to salvage first JSON object.
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise AIAgentError("invalid json")
        try:
            data = json.loads(content[start : end + 1])
        except Exception:
            raise AIAgentError("invalid json")

    if not isinstance(data, dict):
        raise AIAgentError("invalid output type")

    category = data.get("category")
    subtasks = data.get("subtasks")
    if category not in ("personal", "work", "urgent"):
        raise AIAgentError("invalid category")
    if not isinstance(subtasks, list) or not all(isinstance(x, str) for x in subtasks):
        raise AIAgentError("invalid subtasks")

    # Normalize.
    steps = [s.strip() for s in subtasks if s and s.strip()]
    steps = steps[:6]
    if len(steps) < 2:
        raise AIAgentError("not enough subtasks")

    return {"category": category, "subtasks": steps}
