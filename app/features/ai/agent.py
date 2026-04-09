"""AI agent module — Dynamic agent with injectable prompts.

Ejemplo de uso:
    
    # Opción 1: Custom prompt
    result = query_with_prompt(
        prompt="Analiza esta tarea y dame subtasks",
        context={"title": "Mi tarea", "description": "Detalles"}
    )
    
    # Opción 2: Template predefinido
    result = query_with_template(
        template="analyze_task",
        context={"title": "Mi tarea", "description": "Detalles"}
    )
    
    # Opción 3: analyze_task (heredado, usa template)
    result = analyze_task(title="...", description="...")
"""

from typing import Optional, Dict, Any
from enum import Enum
import json
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel

load_dotenv()


class AIAgentError(Exception):
    """Raised when the LLM is unavailable or returns invalid output."""


class TaskCategory(str, Enum):
    """Categorías de tareas soportadas."""
    PERSONAL = "personal"
    WORK = "work"
    URGENT = "urgent"


class TaskAnalysis(BaseModel):
    """Resultado del análisis de una tarea."""
    category: TaskCategory
    subtasks: list[str]


# Templates predefinidos
PROMPT_TEMPLATES = {
    "analyze_task": """Analiza la siguiente tarea y proporciona categoría y subtasks.

Tarea: {title}
Descripción: {description}

Responde en JSON con este formato:
{{"category": "personal|work|urgent", "subtasks": ["paso 1", "paso 2", ...]}}""",
    
    "generate_steps": """Genera los pasos detallados para completar esta tarea:

{context}

Responde con una lista de pasos en JSON: {{"steps": ["paso 1", "paso 2", ...]}}""",
    
    "evaluate_complexity": """Evalúa la complejidad de esta tarea:

{context}

Responde en JSON: {{"complexity": "low|medium|high", "reason": "..."}}""",
}


def _get_llm():
    """Obtiene la instancia de ChatOpenAI configurada."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIAgentError("OPENAI_API_KEY no está configurada")
    
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=api_key
    )


def query_with_prompt(
    prompt: str, 
    context: Optional[Dict[str, Any]] = None,
    json_mode: bool = True
) -> Dict[str, Any]:
    """
    Ejecuta una query con un prompt personalizado e inyectable.
    
    Args:
        prompt: Prompt personalizado (puede tener placeholders {variable})
        context: Dict con variables para rellenar placeholders
        json_mode: Si True, parsea la respuesta como JSON
    
    Returns:
        Dict con la respuesta (parseada como JSON si json_mode=True)
    
    Raises:
        AIAgentError: Si falla la llamada al LLM
    """
    try:
        # Formatear prompt con context si se proporciona
        formatted_prompt = prompt
        if context:
            formatted_prompt = prompt.format(**context)
        
        llm = _get_llm()
        response = llm.invoke(formatted_prompt)
        
        # Parsear respuesta
        content = response.content
        
        if json_mode:
            # Intentar extraer JSON de la respuesta
            try:
                # Buscar JSON en la respuesta
                start = content.find("{")
                end = content.rfind("}") + 1
                if start != -1 and end > start:
                    json_str = content[start:end]
                    return json.loads(json_str)
            except (json.JSONDecodeError, ValueError) as e:
                raise AIAgentError(f"Respuesta del LLM no es JSON válido: {content}") from e
        
        return {"response": content}
    
    except AIAgentError:
        raise
    except Exception as e:
        raise AIAgentError(f"Error al consultar LLM: {str(e)}") from e


def query_with_template(
    template: str,
    context: Dict[str, Any],
    json_mode: bool = True
) -> Dict[str, Any]:
    """
    Ejecuta una query usando un template predefinido.
    
    Args:
        template: Nombre del template (ej: "analyze_task", "generate_steps")
        context: Dict con variables del template
        json_mode: Si True, parsea la respuesta como JSON
    
    Returns:
        Dict con la respuesta
    
    Raises:
        AIAgentError: Si template no existe o falla el LLM
    """
    if template not in PROMPT_TEMPLATES:
        raise AIAgentError(
            f"Template '{template}' no existe. "
            f"Disponibles: {', '.join(PROMPT_TEMPLATES.keys())}"
        )
    
    prompt = PROMPT_TEMPLATES[template]
    return query_with_prompt(prompt, context, json_mode)


def analyze_task(title: str, description: str) -> dict:
<<<<<<< HEAD
    """
    Analiza una tarea y retorna categoría y subtasks (heredado para compatibilidad).
    
    Args:
        title: Título de la tarea
        description: Descripción de la tarea
    
    Returns:
        {"category": "personal|work|urgent", "subtasks": ["paso 1", "paso 2", ...]}
    
    Raises:
        AIAgentError: Si falla el análisis
    """
    result = query_with_template(
        template="analyze_task",
        context={"title": title, "description": description},
        json_mode=True
    )
    
    # Validar estructura
    if "category" not in result or "subtasks" not in result:
        raise AIAgentError(f"Respuesta inválida del agente: {result}")
    
    return result


def register_custom_template(name: str, prompt_template: str) -> None:
    """
    Registra un nuevo template personalizado en tiempo de ejecución.
    
    Args:
        name: Nombre único del template
        prompt_template: Template del prompt (puede tener {placeholders})
    """
    PROMPT_TEMPLATES[name] = prompt_template
=======
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
>>>>>>> cbff08abc599c8e975761beed905bd0b00f6529c
