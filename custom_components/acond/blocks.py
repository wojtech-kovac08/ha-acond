"""Register block policies: give-up tracker and option filtering."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .const import ValueSpec


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


def enabled_block_indexes(
    block_count: int, disabled_blocks: frozenset[int]
) -> tuple[int, ...]:
    """Return the block indexes that have to be polled with these options."""
    return tuple(
        index for index in range(block_count) if index not in disabled_blocks
    )


def enabled_values(
    values: Sequence[ValueSpec],
    circuit_2_keys: frozenset[str],
    circuit_2_enabled: bool,
    disabled_blocks: frozenset[int],
) -> tuple[ValueSpec, ...]:
    """Drop the values that belong to switched off parts of the register map."""
    return tuple(
        spec
        for spec in values
        if (circuit_2_enabled or spec.key not in circuit_2_keys)
        and spec.block not in disabled_blocks
    )
