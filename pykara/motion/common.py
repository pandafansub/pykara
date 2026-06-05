"""Shared motion constants and lightweight protocols."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from pykara.data import Event
from pykara.fbf.timeline import FrameRateSource

SHAD_AUTO_MARKER = "__PYKARA_MOTION_SHAD_AUTO__"
SHAD_SETUP_FRAGMENT = r"\alpha&HFF&\4a&H00&\ko0\xshad0.001\yshad0"


class EventExpander(Protocol):
    """Expand one rendered event into one or more output events."""

    def expand(
        self,
        event: Event,
        framerate: FrameRateSource,
    ) -> list[Event]: ...


class ExpansionQueue(Protocol):
    """Mutable object that can carry queued event expansions."""

    expansion_requests: list[QueuedEventExpansion]


ExpansionPhase = Literal["motion_fbf", "gradient"]

EXPANSION_PHASE_ORDER: dict[ExpansionPhase, int] = {
    "motion_fbf": 0,
    "gradient": 1,
}


@dataclass(slots=True, frozen=True)
class QueuedEventExpansion:
    """A structural event expansion scheduled during template execution."""

    label: str
    phase: ExpansionPhase
    expander: EventExpander


def queued_expansion_for_phase(
    queue: ExpansionQueue,
    phase: ExpansionPhase,
) -> QueuedEventExpansion | None:
    """Return the first queued expansion for ``phase``, when present."""
    for queued_expansion in queue.expansion_requests:
        if queued_expansion.phase == phase:
            return queued_expansion
    return None


def queue_event_expansion(
    queue: ExpansionQueue,
    queued_expansion: QueuedEventExpansion,
) -> None:
    """Append one expansion while preserving the phase execution order."""
    queue.expansion_requests.append(queued_expansion)
    queue.expansion_requests.sort(
        key=lambda expansion: (
            EXPANSION_PHASE_ORDER[expansion.phase],
            getattr(expansion.expander, "step", 0),
        )
    )
