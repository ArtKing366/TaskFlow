# МЕСЯЦ 7 — Проект 2: TaskFlow Workflow Platform

### Изменение vs старая версия

Старая версия была обычным task-manager: пользователи, проекты, задачи, JWT, Redis, Celery.

Для портфолио этого мало, поэтому Project 2 превращаем в **production-style backend для командной работы и автоматизации процессов**.

Это всё ещё не AI-проект — AI/RAG полностью оставляем Project 3.

---

## Что это

**TaskFlow** — backend-платформа для управления рабочими пространствами, проектами и задачами.

По смыслу это упрощённая смесь **Trello + Jira + workflow automation**, но только серверная часть.

Главная идея проекта:

> пользователь создаёт Workspace → добавляет участников → создаёт проекты → создаёт задачи → система отслеживает изменения и автоматически выполняет действия по заданным правилам.

Работодатель открывает `/docs` и видит не просто CRUD, а полноценный API с authentication, authorization, roles, audit log, webhooks, background jobs и automation.

---

## Что умеет

* Регистрация / логин с JWT
* Workspace / Organization
* Приглашение пользователей в Workspace
* Роли: Owner / Admin / Member / Viewer
* Разграничение доступа через RBAC
* CRUD проектов
* CRUD задач
* Назначение задач пользователям
* Статусы и приоритеты
* Tags
* Фильтрация задач
* Поиск по тексту
* Deadline
* Comments / activity
* Audit log всех важных изменений
* Event-driven обработка изменений
* Workflow automations: `WHEN → IF → DO`
* Webhooks для внешних сервисов
* Retry webhook delivery через Celery
* Idempotency для повторных запросов
* Redis cache
* Redis как Celery broker
* Background jobs через Celery
* Notifications
* Pytest + coverage 75%+
* GitHub Actions
* Docker
* Railway deployment
* Swagger UI

---

# Как выглядит система

```text
User
 │
 ▼
Workspace
 │
 ├── Members + Roles
 │
 ├── Projects
 │      │
 │      └── Tasks
 │             ├── Tags
 │             ├── Assignee
 │             └── Deadline
 │
 ├── Automations
 ├── Webhooks
 └── Activity / Audit Log
```

При изменении задачи:

```text
User
 ↓
PUT /tasks/17
 ↓
Task Service
 ↓
PostgreSQL
 ↓
task.updated event
 ├── Audit Log
 ├── Automation Engine
 ├── Notification
 └── Celery → Webhook
```

---

# Структура

```text
taskflow/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── crud.py
│   ├── auth.py
│   ├── permissions.py
│   ├── events.py
│   ├── automation.py
│   ├── celery_app.py
│   ├── celery_tasks.py
│   ├── cache.py
│   └── routers/
│       ├── auth.py
│       ├── workspaces.py
│       ├── projects.py
│       ├── tasks.py
│       ├── automations.py
│       ├── webhooks.py
│       └── activity.py
│
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_workspaces.py
│   ├── test_projects.py
│   ├── test_tasks.py
│   ├── test_permissions.py
│   ├── test_automations.py
│   ├── test_webhooks.py
│   └── test_activity.py
│
├── alembic/
├── .env
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .github/
    └── workflows/
        └── ci.yml
```

Файлы не создаём все заранее. Добавляем их тогда, когда появляется соответствующая ответственность.

---

# Зависимости

### Основные

```text
fastapi
uvicorn
sqlalchemy
alembic
psycopg2-binary
python-dotenv
pydantic[email]
pwdlib[argon2]
PyJWT
redis
celery
pytest
pytest-cov
httpx
```

### Почему auth отличается от старого roadmap

Не используем механически:

```text
python-jose[cryptography]
passlib[bcrypt]
```

Для проекта используем:

```text
pwdlib[argon2]
PyJWT
```

JWT и password hashing должны быть отдельными компонентами.

---

# Шаги

## Шаг 1 — Настройка проекта (день 1)

Папка, `.venv`, зависимости, Git.

`.env`:

```text
DATABASE_URL
REDIS_URL
SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES
```

Поднять PostgreSQL и Redis через Docker.

Проверить:

* FastAPI запускается
* PostgreSQL доступен
* Redis доступен
* `/docs` открывается

---

## Шаг 2 — Модели БД: пользователи и Workspace (дни 2–3)

`database.py`:

* SQLAlchemy engine
* `Base`
* DB session

`models.py`:

### User

```text
id
email
hashed_password
is_active
created_at
```

### Workspace

```text
id
name
created_at
```

### Membership

Связь User ↔ Workspace:

```text
user_id
workspace_id
role
created_at
```

Roles:

```text
owner
admin
member
viewer
```

Главная идея:

```text
User
  ↓
Membership
  ↓
Workspace
```

Один пользователь может находиться в нескольких Workspace.

---

## Шаг 3 — Projects, Tasks, Tags (дни 4–5)

Добавить:

### Project

```text
id
workspace_id
title
description
created_at
updated_at
```

### Task

```text
id
project_id
title
description
status
priority
deadline
assignee_id
created_at
updated_at
```

### Tag

```text
id
workspace_id
name
```

### TaskTag

Many-to-many:

```text
task_id
tag_id
```

Статусы:

```text
todo
in_progress
done
```

Priority:

```text
low
medium
high
```

В этот момент уже должно быть:

```text
Workspace
   ↓
Project
   ↓
Task
```

---

## Шаг 4 — Alembic (день 6)

Настроить:

```text
alembic init alembic
```

Подключить metadata моделей.

Создать initial migration.

Применить:

```text
alembic upgrade head
```

Проверить через DBeaver:

```text
users
workspaces
memberships
projects
tasks
tags
task_tags
```

---

## Шаг 5 — Pydantic schemas (день 7)

`schemas.py`.

Для основных моделей:

```text
Base
Create
Update
Response
```

Отдельно:

```text
Token
TokenData
```

Для ролей, статусов и priority использовать enum-подход, чтобы API не принимал произвольные строки.

---

## Шаг 6 — Authentication (день 8)

`auth.py`.

Реализовать:

* password hashing
* password verification
* JWT creation
* JWT decoding
* `get_current_user`

`routers/auth.py`:

```text
POST /auth/register
POST /auth/login
GET  /auth/me
```

После login:

```text
access_token
token_type
```

---

## Шаг 7 — Workspace + RBAC (дни 9–10)

`permissions.py`.

Реализовать проверки:

```text
is_workspace_member()
require_owner()
require_admin()
require_member()
```

Пример логики:

```text
Viewer
→ читать данные

Member
→ читать + работать с задачами

Admin
→ управлять проектами + участниками

Owner
→ полный доступ
```

Создать:

```text
routers/workspaces.py
```

Основные endpoints:

```text
POST   /workspaces
GET    /workspaces
GET    /workspaces/{id}
POST   /workspaces/{id}/members
DELETE /workspaces/{id}/members/{user_id}
PATCH  /workspaces/{id}/members/{user_id}/role
```

Ключевое правило:

**никакой пользователь не должен получить данные Workspace, в котором он не состоит.**

---

## Шаг 8 — CRUD + business logic (дни 11–12)

`crud.py`.

Projects:

```text
get_projects
get_project
create_project
update_project
delete_project
```

Tasks:

```text
get_tasks
get_task
create_task
update_task
delete_task
complete_task
assign_task
```

Фильтры:

```text
status
priority
tag
assignee
search
deadline
```

Важно:

CRUD должен не просто обращаться к БД.

Он должен учитывать:

```text
current_user
workspace
permissions
ownership
```

---

## Шаг 9 — Events + Audit Log (день 13)

Добавить модель:

### AuditLog

```text
id
workspace_id
user_id
action
entity_type
entity_id
old_value
new_value
created_at
```

Например:

```text
Artem changed task #17

status:
in_progress → done
```

Добавить внутренние события:

```text
task.created
task.updated
task.completed
task.deleted
project.created
member.added
member.removed
```

Событие должно позволять другим частям системы реагировать на изменение, не смешивая всю логику в endpoint.

---

## Шаг 10 — Automation Engine (дни 14–15)

Главная фишка Project 2.

Добавить сущность Automation:

```text
id
workspace_id
name
trigger
condition
action
is_active
created_at
```

Концепция:

```text
WHEN
    task.status == done

IF
    task.priority == high

DO
    send_notification
```

Другой пример:

```text
WHEN task.deadline is approaching
DO send reminder
```

И:

```text
WHEN task is completed
DO send webhook
```

То есть появляется реальный механизм:

```text
Event
 ↓
Automation Engine
 ↓
Conditions
 ↓
Actions
```

---

## Шаг 11 — Webhooks (день 16)

`routers/webhooks.py`.

Пользователь может зарегистрировать endpoint:

```text
POST /webhooks
```

Например:

```text
https://example.com/taskflow-hook
```

События:

```text
task.created
task.updated
task.completed
project.created
```

Когда происходит событие:

```text
TaskFlow
   ↓
Celery
   ↓
HTTP POST
   ↓
external service
```

Хранить информацию о delivery:

```text
WebhookDelivery
├── webhook_id
├── event
├── status
├── attempts
├── last_error
└── created_at
```

---

## Шаг 12 — Celery + retry (день 17)

`celery_app.py`

Redis:

```text
redis://localhost:6379/0
```

`celery_tasks.py`:

* отправка webhook
* notification
* другие тяжёлые фоновые операции

Например:

```text
task.completed
 ↓
Celery
 ↓
send_webhook()
```

При ошибке:

```text
attempt 1
attempt 2
attempt 3
```

После окончательной ошибки:

```text
status = failed
```

Celery здесь используется не ради демонстрации технологии, а потому что webhook delivery и notifications не должны блокировать HTTP-запрос.

---

## Шаг 13 — Redis cache (день 18)

Добавить кэширование подходящих GET-запросов.

Например:

```text
GET /workspaces/{id}/projects
```

или:

```text
GET /projects/{id}/tasks
```

Поток:

```text
FastAPI
 ↓
Redis?
 ├── yes → return cached data
 └── no
      ↓
  PostgreSQL
      ↓
    Redis
      ↓
   response
```

При изменении данных:

```text
create
update
delete
```

соответствующий cache инвалидируется.

---

## Шаг 14 — Idempotency + API robustness (день 19)

Для чувствительных POST-запросов добавить поддержку:

```text
Idempotency-Key
```

Например:

```text
POST /tasks
Idempotency-Key: abc123
```

Если клиент повторил тот же запрос:

```text
abc123 уже обработан
```

не создаётся вторая задача.

Также проверить:

* правильные HTTP status codes
* validation errors
* 401 / 403 / 404
* pagination
* consistent response format
* edge cases

---

## Шаг 15 — Тесты (дни 20–22)

Поскольку месяцу лучше не быть математически привязанным ровно к 20 календарным дням, тесты занимают несколько рабочих дней.

`tests/conftest.py`:

* test database
* TestClient
* users
* workspaces
* authenticated client
* tokens

### `test_auth.py`

Проверить:

```text
register
duplicate email
login
wrong password
/me
```

### `test_workspaces.py`

Проверить:

```text
create workspace
invite member
change role
remove member
access control
```

### `test_permissions.py`

Проверить:

```text
Owner
Admin
Member
Viewer
```

на разных endpoints.

### `test_projects.py`

CRUD + authorization.

### `test_tasks.py`

CRUD + filters:

```text
status
priority
tag
assignee
search
deadline
```

### `test_automations.py`

Проверить:

```text
event
→ condition
→ action
```

### `test_webhooks.py`

Проверить:

```text
delivery
retry
failure
```

Цель:

```text
75%+ coverage
```

---

## Шаг 16 — Docker (дни 23–24)

Создать:

```text
Dockerfile
docker-compose.yml
```

Services:

```text
postgres
redis
app
celery_worker
```

Запуск:

```text
docker-compose up --build
```

Вся система должна подняться без ручного запуска PostgreSQL/Redis.

---

## Шаг 17 — GitHub Actions (день 25)

`.github/workflows/ci.yml`

На:

```text
push
pull_request → main
```

выполняется:

```text
checkout
↓
Python 3.12
↓
install dependencies
↓
run tests
↓
coverage
```

Например:

```text
pytest --cov=app --cov-fail-under=75
```

Цель:

**каждый PR автоматически проверяется.**

---

## Шаг 18 — Railway deployment (дни 26–27)

Задеплоить:

```text
FastAPI
PostgreSQL
Redis
Celery Worker
```

Настроить environment variables.

Проверить:

```text
/live URL
/docs
/auth
/workspaces
/projects
/tasks
```

---

## Шаг 19 — Финальная полировка (день 28)

Проверить весь пользовательский flow:

```text
register
 ↓
login
 ↓
create workspace
 ↓
invite member
 ↓
create project
 ↓
create task
 ↓
assign task
 ↓
change status
 ↓
audit event
 ↓
automation
 ↓
notification / webhook
```

Убедиться, что:

* чужие Workspace недоступны;
* RBAC реально работает;
* automation запускается;
* webhook retry работает;
* Redis cache инвалидируется;
* Celery worker работает отдельно;
* тесты проходят;
* Docker поднимает всё с нуля.

---

## Шаг 20 — README (день 29–30)

README на английском.

Показать:

```text
What is TaskFlow?
Architecture
Features
Tech Stack
Database structure
Authentication
RBAC
Automation Engine
Events
Webhooks
Redis
Celery
Testing
Docker
CI/CD
Deployment
```

Добавить:

* архитектурную схему;
* Swagger URL;
* пример API flow;
* screenshots `/docs`;
* инструкцию локального запуска;
* ссылку на live API.

---

# Финальная архитектура

```text
                         ┌───────────────┐
                         │     Client    │
                         └───────┬───────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │    FastAPI    │
                         └───────┬───────┘
                                 │
       ┌─────────────────────────┼────────────────────────┐
       │                         │                        │
       ▼                         ▼                        ▼
    Auth/RBAC              Projects/Tasks          Automation Engine
       │                         │                        │
       └─────────────────────────┼────────────────────────┘
                                 │
                                 ▼
                         ┌───────────────┐
                         │  PostgreSQL   │
                         └───────┬───────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │                 │                 │
               ▼                 ▼                 ▼
           Audit Log          Events           Webhooks
                                                    │
                                                    ▼
                                                Celery
                                                    │
                           ┌────────────────────────┼──────────┐
                           │                        │          │
                           ▼                        ▼          ▼
                      Notifications             Retries     Delivery

                         ┌───────────────┐
                         │     Redis     │
                         └───────┬───────┘
                                 │
                        cache + Celery broker
```

# Готово когда

Проект считается завершённым, когда:

```text
✅ User registration/login
✅ JWT authentication
✅ Workspace / multi-tenancy
✅ RBAC
✅ Projects
✅ Tasks
✅ Filters / search
✅ Tags
✅ Assignees / deadlines
✅ Audit log
✅ Events
✅ Automation Engine
✅ Webhooks
✅ Celery + retries
✅ Redis cache
✅ Idempotency
✅ Pytest
✅ 75%+ coverage
✅ Docker
✅ GitHub Actions
✅ Railway
✅ Live /docs
✅ README
```

---

# Что этот проект показывает

**FastAPI** — API.

**PostgreSQL + SQLAlchemy** — persistence.

**Alembic** — migrations.

**JWT + RBAC + multi-tenancy** — security and authorization.

**Events + Audit Log** — system design.

**Automation Engine** — business logic.

**Redis** — caching и broker.

**Celery** — background processing и retries.

**Webhooks** — integration with external systems.

**Idempotency** — reliability.

**Pytest** — testing.

**Docker + GitHub Actions + Railway** — delivery.

А Project 3 уже отдельно показывает:

```text
Embeddings
pgvector
RAG
Document ingestion
LLM
SSE
Tool calling
AI search
```

Так у тебя не три одинаковых FastAPI CRUD-проекта, а последовательность:

```text
Project 1
→ фундамент

Project 2
→ production backend + system design

Project 3
→ AI / RAG backend
```
