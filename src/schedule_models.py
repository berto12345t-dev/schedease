"""Domain records used by the SchedEase scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field


DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
DAY_INDEX = {day: index for index, day in enumerate(DAYS)}


def parse_time(value: str) -> int:
    """Convert strict 24-hour HH:MM text to minutes after midnight."""
    text = value.strip()
    if len(text) != 5 or text[2] != ":" or not text[:2].isdigit() or not text[3:].isdigit():
        raise ValueError("Enter time in 24-hour HH:MM format, for example 09:30.")
    hour, minute = int(text[:2]), int(text[3:])
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError(f"'{value}' is not a valid time.")
    return hour * 60 + minute


def format_time(minutes: int) -> str:
    """Format minutes after midnight as 12-hour time."""
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12:02d}:{minute:02d} {suffix}"


@dataclass(frozen=True)
class Meeting:
    day: str
    start: str
    end: str
    subject_code: str
    title: str
    section: str
    blocked: bool = False
    reason: str = ""

    @property
    def day_index(self) -> int:
        return DAY_INDEX[self.day]

    @property
    def start_minute(self) -> int:
        return parse_time(self.start)

    @property
    def end_minute(self) -> int:
        return parse_time(self.end)

    @property
    def key(self) -> int:
        return self.day_index * 1440 + self.start_minute

    @property
    def end_abs(self) -> int:
        return self.day_index * 1440 + self.end_minute


@dataclass
class Section:
    identifier: str
    slots_left: int
    meetings: list[Meeting] = field(default_factory=list)


@dataclass
class Subject:
    code: str
    title: str
    units: int
    sections: list[Section] = field(default_factory=list)
    pinned: bool = False


@dataclass
class ScheduleState:
    next_subject_index: int
    selected_sections: list[tuple[str, Section]]
    units: int
    tree: object


@dataclass
class ScheduleRecommendation:
    state: ScheduleState
    campus_days: int
    idle_gap_minutes: int
    discovery_order: int

    @property
    def rank_key(self) -> tuple[int, int, int, int]:
        return (-self.state.units, self.campus_days, self.idle_gap_minutes, self.discovery_order)


@dataclass
class GenerationResult:
    recommendations: list[ScheduleRecommendation] = field(default_factory=list)
    error: str | None = None
    states_processed: int = 0
    complete_candidates: int = 0
    conflict_rejections: int = 0
    full_section_rejections: int = 0
    unit_cap_rejections: int = 0
    conflict_details: list[str] = field(default_factory=list)


class SchedulingError(ValueError):
    """Raised when user-provided scheduling data is invalid."""
