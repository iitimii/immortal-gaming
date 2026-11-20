# Docker and Production Frontend CI Safeguards

This document records the Docker deployment and production frontend build CI safeguards that have already landed. It is no longer a pending implementation plan, but a reference for maintaining these checks.

## Current Status

Issue #196 once exposed a black browser screen after Docker deployment, caused by the production frontend bundle throwing errors when executed in a real browser. To prevent this kind of problem from recurring, the repository now keeps two layers of CI:

1. `.github/workflows/test.yml`
   - Full backend pytest.
   - Frontend `npm run type-check`.
   - Frontend `npm run test:coverage`.
   - Frontend `npm run build`.
   - Playwright production frontend smoke: `npm run smoke:production`.
2. `.github/workflows/docker-smoke.yml`
   - `docker compose build`.
   - `pytest -m docker tests/test_docker_runtime_smoke.py -v`.
   - Docker frontend browser smoke: access `http://127.0.0.1:8123` through the nginx entry and run Playwright.

The accompanying contract / smoke tests mainly include:

- `tests/test_docker_build_contract.py`
- `tests/test_data_paths_runtime_contract.py`
- `tests/test_docker_runtime_smoke.py`
- `tests/test_nginx_proxy_contract.py`
- `tests/test_server_binding.py`
- `web/e2e/production-smoke.spec.ts`

## Coverage Goals

The current CI must keep covering the following risks:

1. The frontend production build succeeds, but the real browser shows a black screen after executing the JS.
2. The Docker image builds successfully, but the runtime image is missing runtime dependencies.
3. The frontend container health check only hits the static home page and cannot prove the backend proxy chain works.
4. `CWS_DATA_DIR=/data` persistence fails, causing settings / secrets / saves / logs to be lost after container rebuilds.
5. In the Docker scenario, a WebSocket disconnect or no connected clients causes the container to exit automatically.
6. Breaks occur between nginx, static asset paths, the frontend production bundle, and the backend API proxy.

## Maintenance Constraints

When modifying Docker, deployment, the frontend production build, or persistence semantics, keep the following in sync:

1. Dockerfile / compose / nginx configuration.
2. Contract tests that do not depend on the Docker daemon.
3. Smoke tests that depend on Docker.
4. Deployment instructions in `README.md` and `docs/readme/*.md`.

The production image should install only runtime dependencies; do not install test dependencies such as `pytest` into the runtime image. Docker runtime user data is determined solely by `CWS_DATA_DIR`; do not go back to relying on old runtime directories such as `/app/assets/saves` and `/app/logs`.

## Failure Diagnostic Artifacts

When Docker-related workflows fail, try to keep the following artifacts:

1. `docker compose ps`
2. backend / frontend container logs
3. Playwright report, trace, screenshot
4. The `web/dist` file listing

This information helps quickly determine whether the problem lies in backend startup, the nginx proxy, static assets, production JS execution, or first-screen rendering.

## Pre-Release Recommendations

Before a release, it is recommended to confirm at least that the following commands pass in CI or locally:

```bash
pytest
cd web && npm run type-check
cd web && npm run test
cd web && npm run build
cd web && npm run smoke:production
pytest -m docker tests/test_docker_runtime_smoke.py -v
```

If Docker is not available locally, use the GitHub Actions `Docker Smoke` workflow as the pre-release confirmation entry for Docker.
