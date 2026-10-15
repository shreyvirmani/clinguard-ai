"""Component B (provider side): where baseline responses come from.

The offline demo uses `FixtureProvider`, which returns the hand-written fixture attached to
each case. To evaluate a real model later, implement `ResponseProvider` (see README,
"Replacing fixtures with a real model") and pass it to `run_benchmark(provider=...)`.
"""

from __future__ import annotations

from typing import Any, Protocol


class ResponseProvider(Protocol):
    name: str

    def get_response(self, case: Any) -> str:
        """Return the assistant's response text for `case.input`."""
        ...


class FixtureProvider:
    """Returns the controlled demonstration fixture stored on the case. No model is called."""

    name = "offline-fixtures"

    def get_response(self, case: Any) -> str:
        return case.baseline_response


class LiveModelProvider:
    """Placeholder for a real model adapter. NOT IMPLEMENTED in this prototype."""

    name = "live-model (not implemented)"

    def get_response(self, case: Any) -> str:
        raise NotImplementedError(
            "Live model integration is not implemented in this prototype. "
            "See README section 'Replacing fixtures with a real model'."
        )
