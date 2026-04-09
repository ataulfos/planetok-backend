# planetok-taskai-backend

Backend para la prueba técnica **Fullstack AI (Pair Programming) — Planet OK**.
Gestor de tareas asistido por un agente de IA (Langchain + OpenAI).

> Pair programming: **Gonzalo** (backend) · **Eduardo** (frontend).

## Stack

- Python 3.12
- **FastAPI** + SQLAlchemy 2.0
- PostgreSQL 16
- Langchain + OpenAI (`gpt-4o-mini`)
- pytest + httpx
- Docker + Docker Compose

## Estructura (feature-based)

```
app/
├── main.py                 # FastAPI app + CORS + routers
├── core/
│   ├── config.py           # Settings (pydantic-settings)
│   ├── database.py         # engine, Base, get_db
│   └── deps.py             # get_current_user (sim)
├── features/
│   ├── auth/               # User model + /auth endpoints
│   ├── tasks/              # Task + Subtask + /api/tasks endpoints
│   └── ai/                 # Langchain agent (analyze_task)
└── models.py               # SQLAlchemy metadata aggregator
tests/
docs/
└── API.md                  # Contrato API para el frontend
```

## Cómo correrlo

```bash
cp .env.example .env        # editar OPENAI_API_KEY
docker compose up --build
```

| Servicio  | URL                     |
| --------- | ----------------------- |
| Backend   | http://localhost:3001   |
| Postgres  | localhost:5432          |
| Frontend  | http://localhost:3000   |

Health check:
```bash
curl http://localhost:3001/health
# {"status":"ok"}
```

## Tests

```bash
docker compose exec backend pytest -v
```

O localmente:
```bash
pip install -r requirements.txt
pytest -v
```

## Contrato API

Ver [`docs/API.md`](docs/API.md) para la lista completa de endpoints,
request/response shapes y tipos TypeScript listos para copiar.

## Branches

- `main`  — código estable, lo que Eduardo consume
- `dev`   — integración, merges de features

## Mejoras futuras (fuera de scope por tiempo)

- [ ] Hashing de passwords (bcrypt) + JWT real en lugar de `X-User-Id`
- [ ] Alembic migrations en lugar de `Base.metadata.create_all`
- [ ] CORS restrictivo por origen
- [ ] Rate limiting en `/api/tasks/{id}/analyze/`
- [ ] Caching de respuestas del LLM
- [ ] CI con GitHub Actions (lint + tests + docker build)
