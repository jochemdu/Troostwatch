## fix: resolve tracing merge-conflict and final mypy fixes

This pull request applies conservative, low-risk fixes to get the repository back
into a clean, testable state while preserving runtime behavior.

- Remove merge-conflict residue in `troostwatch/infrastructure/observability/tracing.py` (SyntaxError)
- Fix remaining mypy errors in `troostwatch/services/sync/sync.py` and `troostwatch/services/label_extraction.py`
- Minor, conservative typing/coercion fixes across services and API to satisfy `pydantic` and `mypy`

Testing summary
- Local typecheck: `mypy troostwatch` — no issues found
- Local tests: `pytest -q` — `197 passed`

Notes & rationale
- Changes were intentionally small and targeted to avoid behavioral regressions:
  - Widened a few `Mapping`/`Optional` types where appropriate
  - Added a missing variable annotation and a missing return-path to satisfy mypy
  - Replaced a few ad-hoc dict-unpacks with explicit Pydantic model construction where needed

Next steps (suggested)
- Run CI and confirm all checks pass in the PR pipeline
- Triage remaining TODOs in the repo (see `TODO` list in project root)

Related PR: https://github.com/jochemdu/Troostwatch/pull/82

Signed-off-by: repo-maintainer <noreply@example.com>
