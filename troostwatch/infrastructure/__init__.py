"""Infrastructure layer for Troostwatch.

Holds adapters for HTTP, persistence, parsing and diagnostics. Modules in this
package wrap legacy implementations so callers can migrate to the layered
layout incrementally.
"""

__all__ = ["diagnostics", "http", "observability", "persistence", "web"]
