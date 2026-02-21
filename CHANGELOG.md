# Changelog

## [Unreleased]

### Added

- Эндпоинт **GET /ready** для проверки готовности сервиса (readiness). Возвращает `{ "ready": true }`.
- Схема `ReadyResponse` в API.
- В Kubernetes readinessProbe переведён на путь `/ready` (liveness остаётся на `/health`).
- Тест `test_ready_check` для GET /ready.
