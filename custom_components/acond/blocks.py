"""Tracking of register blocks the unit refuses (no Home Assistant imports)."""

from __future__ import annotations


class BlockTracker:
    """Remember which register blocks the unit does not implement.

    A block is given up after ``max_errors`` consecutive Modbus exception
    responses. Transient problems (timeouts, lost connection) do not count,
    because those are retried on the next poll.
    """

    def __init__(self, max_errors: int = 3) -> None:
        self.max_errors = max_errors
        self._errors: dict[int, int] = {}
        self._unsupported: set[int] = set()

    def should_read(self, start: int) -> bool:
        """Return False once the block has been given up."""
        return start not in self._unsupported

    def record_success(self, start: int) -> None:
        """Reset the error counter of a block."""
        self._errors.pop(start, None)
        self._unsupported.discard(start)

    def record_error(self, start: int) -> bool:
        """Count an exception response; return True when the block is dropped."""
        count = self._errors.get(start, 0) + 1
        self._errors[start] = count
        if count >= self.max_errors:
            self._unsupported.add(start)
            return True
        return False

    @property
    def unsupported(self) -> set[int]:
        """Blocks that are no longer polled."""
        return set(self._unsupported)

    @property
    def pending(self) -> dict[int, int]:
        """Error counters of the blocks that still fail occasionally."""
        return dict(self._errors)
