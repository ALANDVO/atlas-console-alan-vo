# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

markdown-renderer

## Roadmap

### core-skeleton — Core FastAPI/React skeleton with auth and basic dashboard

Status: done

Acceptance:
- FastAPI app starts with SQLite backend
- React frontend builds and serves login page
- OIDC/Keycloak auth flow works (login/logout)
- Protected dashboard route accessible after login
- Docker compose spins up backend, frontend, Keycloak, PostgreSQL
- Backend tests pass (pytest), frontend tests pass (vitest)
- CI workflow runs backend/frontend tests and Docker builds

Implementation: `backend/app/main.py`, `backend/app/api/auth.py`, `backend/app/api/dashboard.py`, `backend/app/core/config.py`, `backend/app/core/security.py`, `backend/app/core/database.py`, `backend/app/models/user.py`, `backend/app/services/auth_service.py`, `backend/requirements.txt`, `backend/Dockerfile`, `backend/tests/test_auth.py`, `backend/tests/test_dashboard.py`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/Login.tsx`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/Layout.tsx`, `frontend/src/api/client.ts`, `frontend/src/hooks/useAuth.ts`, `frontend/Dockerfile`, `compose.yaml`, `.env.example`, `.github/workflows/ci.yml`

Tests: `backend/tests/test_auth.py`, `backend/tests/test_dashboard.py`, `frontend/src/pages/Login.test.tsx`, `frontend/src/pages/Dashboard.test.tsx`

### markdown-renderer — Markdown renderer with proper code block handling

Status: planned

Acceptance:
- Triple backticks inside code blocks render as literal text
- Nested code blocks don't break page layout
- Markdown component reusable across dashboard

Implementation: `frontend/src/components/MarkdownRenderer.tsx`, `frontend/src/components/MarkdownRenderer.test.tsx`

Tests: `frontend/src/components/MarkdownRenderer.test.tsx`

### scope-management — Scope of work management (IP ranges, ports, services)

Status: planned

Acceptance:
- CRUD for scope entries (IP/CIDR, port ranges, service names)
- Scope validation during agent task execution
- Import/export scope as JSON/YAML

Implementation: `backend/app/api/scope.py`, `backend/app/models/scope.py`, `backend/app/services/scope_service.py`, `backend/tests/test_scope.py`, `frontend/src/pages/Scope.tsx`, `frontend/src/api/scope.ts`

Tests: `backend/tests/test_scope.py`, `frontend/src/pages/Scope.test.tsx`

### resource-library — Paginated resource library with virtual scrolling

Status: planned

Acceptance:
- Resources load in pages (not full 29MB fetch)
- Virtual scrolling for large lists
- Search and filter by type, tags, date

Implementation: `backend/app/api/resources.py`, `backend/app/models/resource.py`, `backend/app/services/resource_service.py`, `backend/tests/test_resources.py`, `frontend/src/pages/Resources.tsx`, `frontend/src/components/VirtualList.tsx`, `frontend/src/api/resources.ts`

Tests: `backend/tests/test_resources.py`, `frontend/src/pages/Resources.test.tsx`

### mcp-client — MCP client for external security tools

Status: planned

Acceptance:
- Configure MCP servers via env (stdio, SSE, HTTP)
- Auto-discover tools at startup
- Expose tools to agents as callable functions

Implementation: `backend/app/services/mcp_client.py`, `backend/app/models/mcp.py`, `backend/app/api/mcp.py`, `backend/tests/test_mcp.py`, `frontend/src/pages/MCP.tsx`, `frontend/src/api/mcp.ts`

Tests: `backend/tests/test_mcp.py`, `frontend/src/pages/MCP.test.tsx`

### llm-provider-ui — Web UI for custom LLM provider configuration

Status: planned

Acceptance:
- Create/test OpenAI-compatible providers in UI
- Encrypted credential storage
- Model discovery via /v1/models
- Assign models to agent roles

Implementation: `backend/app/api/providers.py`, `backend/app/models/provider.py`, `backend/app/services/provider_service.py`, `backend/tests/test_providers.py`, `frontend/src/pages/Providers.tsx`, `frontend/src/api/providers.ts`

Tests: `backend/tests/test_providers.py`, `frontend/src/pages/Providers.test.tsx`

### penetration-flows — Autonomous penetration testing flows

Status: planned

Acceptance:
- Create/manage penetration test flows
- Agent orchestration (recon, scan, exploit, report)
- Flow execution with progress tracking
- Results export

Implementation: `backend/app/api/flows.py`, `backend/app/models/flow.py`, `backend/app/services/flow_service.py`, `backend/app/services/agent_orchestrator.py`, `backend/tests/test_flows.py`, `frontend/src/pages/Flows.tsx`, `frontend/src/pages/FlowDetail.tsx`, `frontend/src/api/flows.ts`

Tests: `backend/tests/test_flows.py`, `frontend/src/pages/Flows.test.tsx`, `frontend/src/pages/FlowDetail.test.tsx`

