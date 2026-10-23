# Changelog

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.0.1 - 2024-10-23

### Added
- MarkdownRenderer component with proper nested code block handling
- Triple backticks inside fenced code blocks now render as literal text
- Support for fenced code blocks (``` and ~~~), headings, blockquotes, lists, links, bold, italic, inline code
- HTML escaping for XSS prevention
- Comprehensive test suite (39 tests)

### Fixed
- Issue where nested triple backticks inside code blocks were incorrectly interpreted as closing fences

## 1.0.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-10-15

### Added
- FastAPI backend with SQLite/PostgreSQL support
- React + TypeScript + Vite frontend
- OIDC/Keycloak authentication with PKCE
- Role-based access control (viewer, operator, admin)
- Demo mode for local development
- Dashboard with stats, recent activity, quick actions
- Docker Compose with backend, frontend, Keycloak, PostgreSQL
- Health checks for all services
- CI pipeline (backend tests, frontend tests, Docker builds)
- Keycloak realm import with pre-configured clients and users
- Structured logging with structlog
- Comprehensive test suite (pytest + vitest)

### Security
- HttpOnly SameSite cookies for session management
- JWT access/refresh tokens with rotation
- bcrypt password hashing
- CSRF protection on state-changing operations
- Input validation with Pydantic
- No hardcoded secrets

### Infrastructure
- Non-root Docker users
- .dockerignore for both services
- Development ports bound to 127.0.0.1
- Persistent volumes for database and Keycloak data
- TLS reverse proxy documentation