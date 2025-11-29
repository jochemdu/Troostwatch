# Troostwatch Documentation

This directory contains extended documentation for the Troostwatch project.

## Quick Start

- **[Architecture](architecture.md)** – Layered architecture overview and import rules
- **[API Reference](api.md)** – REST API endpoints, WebSocket, and TypeScript types
- **[Database](db.md)** – Schema documentation and table definitions
- **[Contributing](contributing.md)** – Code review checklist and patterns

## Core Documentation

| Document | Description |
|----------|-------------|
| [Architecture](architecture.md) | System design, layer rules, and import enforcement |
| [API Reference](api.md) | REST endpoints, stability policy, TypeScript types |
| [Database Schema](db.md) | Table definitions, relationships, and indexes |
| [Sync Service](sync.md) | Data flow, HTTP fetching, and change detection |
| [Observability](observability.md) | Logging, metrics, and monitoring strategy |

## Development Guides

| Document | Description |
|----------|-------------|
| [Contributing](contributing.md) | Code patterns, where to put new code |
| [Review Checklist](review_checklist.md) | PR review guidelines for reviewers |
| [Migration Policy](migration_policy.md) | Database schema change workflow |
| [Versioning](versioning.md) | SemVer policy and version locations |

## Reference

| Document | Description |
|----------|-------------|
| [Feature Status](feature_status.md) | Implementation status of key features |
| [API Route Mapping](api_route_service_mapping.md) | Route-to-service mapping (Dutch) |
| [Grafana Dashboard](grafana_dashboard.md) | Reference dashboard for Prometheus metrics |

## Agent Guidelines

Role-specific agent instructions are in `.github/agents/`. See
[AGENTS.md](../AGENTS.md) for project-wide guidelines.