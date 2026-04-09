# API Contract — TaskAI Backend

Documento **definitivo** para integración frontend. Los shapes son estables:
el frontend puede empezar a tipear y conectar contra este contrato aunque
los endpoints aún estén en desarrollo.

## Convenciones globales

| Item              | Valor                                     |
| ----------------- | ----------------------------------------- |
| Base URL          | `http://localhost:3001`                   |
| Content-Type      | `application/json`                        |
| Auth (simulada)   | Header `X-User-Id: <uuid>` en `/api/*`    |
| Fechas            | ISO 8601 UTC (`2026-04-09T14:23:11.123Z`) |
| IDs               | UUID v4 string                            |
| Error shape       | `{ "detail": "mensaje humano" }`          |
| CORS              | `*` (abierto en demo)                     |

**Flujo de "sesión":** el frontend hace `POST /auth/login`, recibe el `User`,
guarda `user.id` en `localStorage`, y lo envía como header `X-User-Id` en
cada request subsiguiente. No hay JWT todavía (mejora futura).

---

## Tipos TypeScript (copiar tal cual)

```typescript
export type TaskStatus = "pending" | "completed";
export type TaskCategory = "personal" | "work" | "urgent" | null;

export interface User {
  id: string;
  username: string;
  created_at: string;
}

export interface Subtask {
  id: string;
  title: string;
  order: number;
  completed: boolean;
}

export interface Task {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  category: TaskCategory;
  created_at: string;
  updated_at: string;
  subtasks: Subtask[];
}

export interface ErrorResponse {
  detail: string;
}
```

---

## Endpoints

### Health

#### `GET /health`
Sin auth. Para liveness checks.

**Response `200`:**
```json
{ "status": "ok" }
```

---

### Auth

#### `POST /auth/register`
Crea un usuario. Password en plaintext (sim).

**Request body:**
```json
{ "username": "gonza", "password": "1234" }
```

**Responses:**
| Status | Body                                                         |
| ------ | ------------------------------------------------------------ |
| `201`  | `User`                                                       |
| `409`  | `{ "detail": "username already exists" }`                    |
| `422`  | Validación pydantic (username/password vacíos)               |

#### `POST /auth/login`
Valida credenciales. El frontend guarda `id` y lo reusa como `X-User-Id`.

**Request body:**
```json
{ "username": "gonza", "password": "1234" }
```

**Responses:**
| Status | Body                                          |
| ------ | --------------------------------------------- |
| `200`  | `User`                                        |
| `401`  | `{ "detail": "invalid credentials" }`         |

---

### Tasks

> Todas las rutas de `/api/tasks/*` requieren header `X-User-Id: <uuid>`.
> Sin header o con id inválido → `401 { "detail": "..." }`.
> Las tareas están **scopeadas por usuario**: un user nunca ve tareas de otro.

#### `GET /api/tasks/`
Lista las tareas del usuario autenticado.

**Query params** (todos opcionales):
| Param      | Valores                                            | Default       |
| ---------- | -------------------------------------------------- | ------------- |
| `status`   | `pending` \| `completed`                           | (sin filtro)  |
| `ordering` | `created_at` \| `-created_at` \| `updated_at` \| `-updated_at` | `-created_at` |

**Ejemplos:**
- `GET /api/tasks/` → todas, recientes primero
- `GET /api/tasks/?status=pending` → solo pendientes
- `GET /api/tasks/?status=completed&ordering=updated_at`

**Response `200`:** `Task[]`
```json
[
  {
    "id": "3f9a...",
    "title": "Preparar presentación",
    "description": "Slides para el lunes",
    "status": "pending",
    "category": "work",
    "created_at": "2026-04-09T14:23:11.123Z",
    "updated_at": "2026-04-09T14:25:00.000Z",
    "subtasks": [
      { "id": "7b2c...", "title": "Reunir datos", "order": 0, "completed": false },
      { "id": "8a1d...", "title": "Diseñar slides", "order": 1, "completed": false }
    ]
  }
]
```

#### `POST /api/tasks/`
Crea una tarea. La categoría queda `null` hasta que se llame `/analyze/`.

**Request body:**
```json
{ "title": "Preparar presentación", "description": "Slides para el lunes" }
```

**Responses:**
| Status | Body                                    |
| ------ | --------------------------------------- |
| `201`  | `Task` (con `subtasks: []`)             |
| `422`  | `title` vacío o faltante                |

#### `GET /api/tasks/{id}/`
Detalle de una tarea del usuario (con subtasks anidadas).

**Responses:**
| Status | Body                           |
| ------ | ------------------------------ |
| `200`  | `Task`                         |
| `404`  | `{ "detail": "task not found" }` (no existe o no es del user) |

#### `PATCH /api/tasks/{id}/`
Update parcial. Todos los campos son opcionales. Usado principalmente para
marcar completada (`{ "status": "completed" }`).

**Request body:**
```json
{
  "title": "...",
  "description": "...",
  "status": "completed",
  "category": "work"
}
```

**Responses:**
| Status | Body                           |
| ------ | ------------------------------ |
| `200`  | `Task` actualizada             |
| `404`  | `{ "detail": "task not found" }` |
| `422`  | Validación (status/category inválido) |

#### `DELETE /api/tasks/{id}/`
Elimina la tarea (y sus subtasks por cascade).

**Responses:**
| Status | Body   |
| ------ | ------ |
| `204`  | —      |
| `404`  | `{ "detail": "task not found" }` |

#### `POST /api/tasks/{id}/analyze/`
**Dispara el agente de IA.** El agente:
1. Clasifica la tarea (`personal` | `work` | `urgent`)
2. Sugiere subtareas (2-6 pasos accionables)
3. Persiste `category` en la task y crea las `Subtask` rows

Request body: vacío.

**Response `200`:** `Task` completa con `category` poblada y `subtasks` recién creadas.
El frontend puede reemplazar la task en su state con esta respuesta directamente.

```json
{
  "id": "3f9a...",
  "title": "Preparar presentación",
  "description": "Slides para el lunes",
  "status": "pending",
  "category": "work",
  "created_at": "...",
  "updated_at": "...",
  "subtasks": [
    { "id": "...", "title": "Reunir datos de ventas", "order": 0, "completed": false },
    { "id": "...", "title": "Diseñar 10 slides", "order": 1, "completed": false },
    { "id": "...", "title": "Revisar con el equipo", "order": 2, "completed": false }
  ]
}
```

**Errores:**
| Status | Body                                          |
| ------ | --------------------------------------------- |
| `404`  | `{ "detail": "task not found" }`              |
| `502`  | `{ "detail": "ai agent unavailable" }`        |
| `504`  | `{ "detail": "ai agent timeout" }`            |

> **Nota para el frontend:** si `analyze` ya fue llamado antes, volver a
> llamarlo **reemplaza** las subtasks existentes (no acumula).

#### `PATCH /api/tasks/{task_id}/subtasks/{subtask_id}/`
Toggle del campo `completed` de una subtask.

**Request body:**
```json
{ "completed": true }
```

**Responses:**
| Status | Body                                     |
| ------ | ---------------------------------------- |
| `200`  | `Subtask` actualizada                    |
| `404`  | `{ "detail": "subtask not found" }`      |

---

## Ejemplos curl (smoke test)

```bash
BASE=http://localhost:3001

# 1. Registro + login
curl -X POST $BASE/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"gonza","password":"1234"}'

USER_ID=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"gonza","password":"1234"}' | jq -r .id)

# 2. Crear task
TASK_ID=$(curl -s -X POST $BASE/api/tasks/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d '{"title":"Preparar demo","description":"Ensayar presentación final"}' \
  | jq -r .id)

# 3. Analizar con IA
curl -X POST $BASE/api/tasks/$TASK_ID/analyze/ \
  -H "X-User-Id: $USER_ID"

# 4. Listar pendientes
curl "$BASE/api/tasks/?status=pending" \
  -H "X-User-Id: $USER_ID"

# 5. Marcar completada
curl -X PATCH $BASE/api/tasks/$TASK_ID/ \
  -H "Content-Type: application/json" \
  -H "X-User-Id: $USER_ID" \
  -d '{"status":"completed"}'
```

---

## Estado de implementación

| Endpoint                                    | Estado   |
| ------------------------------------------- | -------- |
| `GET  /health`                              | ✅ ready |
| `POST /auth/register`                       | 🟡 in progress (feat/auth) |
| `POST /auth/login`                          | 🟡 in progress (feat/auth) |
| `GET  /api/tasks/`                          | 🟡 in progress (feat/tasks) |
| `POST /api/tasks/`                          | 🟡 in progress (feat/tasks) |
| `GET  /api/tasks/{id}/`                     | 🟡 in progress (feat/tasks) |
| `PATCH /api/tasks/{id}/`                    | 🟡 in progress (feat/tasks) |
| `DELETE /api/tasks/{id}/`                   | 🟡 in progress (feat/tasks) |
| `POST /api/tasks/{id}/analyze/`             | 🟡 in progress (feat/ai + feat/tasks) |
| `PATCH /api/tasks/{tid}/subtasks/{sid}/`    | 🟡 in progress (feat/tasks) |
