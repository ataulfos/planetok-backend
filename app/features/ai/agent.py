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

from __future__ import annotations

import json
import os
from enum import Enum
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings

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
PROMPT_TEMPLATES: dict[str, str] = {
    "classify_task": """Clasifica la siguiente tarea en una de estas categorías: personal, work, urgent.

Tarea: {title}
Descripción: {description}

Responde en JSON con este formato:
{{"category": "personal|work|urgent"}}""",

    "suggest_subtasks": """Sugiere subtareas accionables para completar esta tarea.

Tarea: {title}
Descripción: {description}
Categoría: {category}

Responde en JSON con este formato:
{{"subtasks": ["paso 1", "paso 2", "..."]}}

Reglas:
- Devuelve entre 2 y 6 subtareas.
- No incluyas texto fuera del JSON.""",
    
    "generate_steps": """Genera los pasos detallados para completar esta tarea:

{context}

Responde con una lista de pasos en JSON: {{"steps": ["paso 1", "paso 2", ...]}}""",
    
    "evaluate_complexity": """Evalúa la complejidad de esta tarea:

{context}

Responde en JSON: {{"complexity": "low|medium|high", "reason": "..."}}""",
}


def _get_llm():
    """Obtiene la instancia de ChatOpenAI configurada."""
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AIAgentError("OPENAI_API_KEY no está configurada")
    
    return ChatOpenAI(
        model=settings.OPENAI_MODEL or "gpt-4o-mini",
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
    """
    Analiza una tarea en 2 pasos (secuencial):
    1) Clasificación (category)
    2) Sugerencia de subtareas (subtasks)
    
    Args:
        title: Título de la tarea
        description: Descripción de la tarea
    
    Returns:
        {"category": "personal|work|urgent", "subtasks": ["paso 1", "paso 2", ...]}
    
    Raises:
        AIAgentError: Si falla el análisis
    """
    step1 = query_with_template(
        template="classify_task",
        context={"title": title, "description": description},
        json_mode=True,
    )
    category = step1.get("category")
    if category not in ("personal", "work", "urgent"):
        raise AIAgentError(f"Respuesta inválida del agente (category): {step1}")

    step2 = query_with_template(
        template="suggest_subtasks",
        context={"title": title, "description": description, "category": category},
        json_mode=True,
    )
    subtasks = step2.get("subtasks")
    if (
        not isinstance(subtasks, list)
        or not all(isinstance(x, str) and x.strip() for x in subtasks)
        or not (2 <= len(subtasks) <= 6)
    ):
        raise AIAgentError(f"Respuesta inválida del agente (subtasks): {step2}")

    return {"category": category, "subtasks": [s.strip() for s in subtasks]}


def register_custom_template(name: str, prompt_template: str) -> None:
    """
    Registra un nuevo template personalizado en tiempo de ejecución.
    
    Args:
        name: Nombre único del template
        prompt_template: Template del prompt (puede tener {placeholders})
    """
    PROMPT_TEMPLATES[name] = prompt_template
