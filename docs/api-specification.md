# API Specification

## URL Shortener
- `POST /api/v1/urls`: create short URL.
- `GET /api/v1/urls/{code}`: retrieve metadata.
- `DELETE /api/v1/urls/{code}`: deactivate.
- `GET /api/v1/urls/{code}/analytics`: click counts.
- `GET /{code}`: HTTP 302 redirect.

## Orchestrator
- `POST /api/workflows`: create workflow.
- `GET /api/workflows/{id}`: workflow state.
- `GET /api/workflows/{id}/tasks`: task graph.
- `GET /api/workflows/{id}/artifacts`: generated artifacts.
- `GET /api/workflows/{id}/audit`: audit history.
- `POST /api/workflows/{id}/approve`: approve pending design gate and resume.
- `POST /api/workflows/{id}/reject`: reject and safe-stop.
- `POST /api/workflows/{id}/replan`: submit changed requirement and re-run impacted planning.
