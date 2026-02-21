---
name: Health checks и документация
overview: Расширить существующий механизм health checks эндпоинтом readiness (GET /ready), добавить тесты, создать план в .md, API.md и CHANGELOG.md, после изменений кода запускать make lint и make test.
todos: []
isProject: false
---

# План: расширение health checks и обновление документации

## Текущее состояние

- Уже есть **GET /health** в [app/api/routes/health.py](app/api/routes/health.py): возвращает `status`, `version`.
- В [k8s/api-deployment.yaml](k8s/api-deployment.yaml) для liveness и readiness используется один и тот же путь `/health`.
- Файлов **API.md** и **CHANGELOG.md** в репозитории нет — их нужно создать.
- Тесты: [tests/test_api.py](tests/test_api.py) — есть `test_health_check`, отдельного теста для readiness нет.

## Что делаем

1. **Эндпоинт readiness**
  Добавить **GET /ready** в [app/api/routes/health.py](app/api/routes/health.py):
  - Простая реализация: возвращать JSON с полем `ready: true` (и при желании `status`), без сложных проверок.
  - Добавить схему ответа в [app/models/schemas.py](app/models/schemas.py) (например `ReadyResponse`: `ready: bool`).
  - Код намеренно простой, без лишней логики.
2. **Kubernetes**
  В [k8s/api-deployment.yaml](k8s/api-deployment.yaml) для **readinessProbe** сменить `path` с `/health` на `/ready`, чтобы liveness оставался на `/health`, а readiness — на `/ready`.
3. **Тесты**
  В [tests/test_api.py](tests/test_api.py) добавить тест для GET `/ready` (status 200, в теле `ready: true`).
4. **Документация и план**
  - Создать файл плана фичи, например **docs/health-checks-feature.md** (или **FEATURE-HEALTH-CHECKS.md** в корне): кратко описать, что сделано (эндпоинты `/health` и `/ready`), зачем, и что после изменений кода нужно запускать `make lint` и `make test`.
  - Создать **API.md**: описание REST API (корень `/`, `/health`, `/ready`, основные группы `/api/models`, `/api/datasets` с примерами путей и ответов).
  - Создать **CHANGELOG.md**: одна запись о добавлении эндпоинта readiness и обновлении health checks (формат Keep a Changelog или простой список).
5. **Линтеры и тесты после изменений кода**
  После любых правок в коде:
  - `make lint` (flake8 + mypy);
  - `make test` (pytest).

## Порядок выполнения

- Написать код (schemas + health routes + k8s readiness path) → **make lint**, **make test**.
- Добавить тест для `/ready` → **make lint**, **make test**.
- Создать docs/health-checks-feature.md (план), API.md, CHANGELOG.md.

## Важные файлы


| Назначение         | Файл                                                       |
| ------------------ | ---------------------------------------------------------- |
| Роуты health/ready | [app/api/routes/health.py](app/api/routes/health.py)       |
| Схемы ответов      | [app/models/schemas.py](app/models/schemas.py)             |
| Подключение роутов | [app/api/main.py](app/api/main.py) (уже подключает health) |
| Пробы в k8s        | [k8s/api-deployment.yaml](k8s/api-deployment.yaml)         |
| API-тесты          | [tests/test_api.py](tests/test_api.py)                     |
