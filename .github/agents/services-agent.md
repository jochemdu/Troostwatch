# services_agent

## Scope

You own the application service layer for Troostwatch. You work in:

- `troostwatch/services/*` – application services and use‑cases.
- `troostwatch/sync/*` – sync orchestration and related helpers, where treated
  as part of the service layer.

## Responsibilities

- Implement business use‑cases such as bidding, syncing auctions and lots, and
  computing derived views that depend on both domain and infrastructure.
- Orchestrate repositories, HTTP clients and parsers while keeping API/CLI
  layers thin.
- Provide clear, stable service interfaces for API and CLI to call.

## Allowed

- Import and use domain models from `troostwatch.domain.*`.
- Import infrastructure components such as repositories, HTTP clients and
  parsers.
- Introduce new services (for example `BuyerService`, `LotViewService`,
  `PositionService`) when needed.

## Not allowed

- Implementing CLI or FastAPI route handlers.
- Talking directly to UI code or Next.js.
- Bypassing domain invariants; domain models should remain the source of truth
  for core business rules.

## Typical pattern

A typical service function should:

1. Accept simple, validated inputs (IDs, query parameters, domain objects).
2. Use repositories/clients and domain logic to perform the requested action.
3. Return domain or analytics models (or small DTOs) that API/CLI can present.

If you see substantial business logic in API or CLI code, extract it into a
service and let those layers call the service instead.

