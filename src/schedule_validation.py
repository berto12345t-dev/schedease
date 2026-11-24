"""Input validation for subjects, sections, meetings, and blocked periods."""

from __future__ import annotations

from schedule_models import DAYS, Meeting, SchedulingError, parse_time


def validate_day(value: str) -> str:
    text = value.strip().lower()
    for day in DAYS:
        if day.lower() == text:
            return day
    raise SchedulingError("Choose a day from Monday through Saturday.")


def validate_meeting(
    day: str,
    start: str,
    end: str,
    subject_code: str,
    title: str,
    section: str,
    *,
    blocked: bool = False,
    reason: str = "",
) -> Meeting:
    if not start.strip() or not end.strip() or start.strip().upper() == "TBA" or end.strip().upper() == "TBA":
        raise SchedulingError("Meeting start and end times are required; TBA schedules are not accepted.")
    canonical_day = validate_day(day)
    try:
        start_minute = parse_time(start)
        end_minute = parse_time(end)
    except ValueError as exc:
        raise SchedulingError(str(exc)) from exc
    opening = 7 * 60
    closing = 21 * 60
    if start_minute < opening or start_minute >= closing:
        raise SchedulingError("Class start time must be between 07:00 and 21:00.")
    if end_minute <= opening or end_minute > closing:
        raise SchedulingError("Class end time must be after 07:00 and no later than 21:00.")
    if end_minute <= start_minute:
        raise SchedulingError("End time must be later than start time on the same day.")
    return Meeting(
        day=canonical_day,
        start=f"{start_minute // 60:02d}:{start_minute % 60:02d}",
        end=f"{end_minute // 60:02d}:{end_minute % 60:02d}",
        subject_code=subject_code.strip().upper(),
        title=title.strip(),
        section=section.strip(),
        blocked=blocked,
        reason=reason.strip(),
    )


def validate_subject_fields(code: str, title: str, units: int | str) -> tuple[str, str, int]:
    normalized_code = code.strip().upper()
    normalized_title = title.strip()
    if not normalized_code:
        raise SchedulingError("Subject code is required.")
    if normalized_code == "BLOCKED":
        raise SchedulingError("BLOCKED is reserved for user-defined blocked periods.")
    if not normalized_title:
        raise SchedulingError("Course title cannot be empty.")
    try:
        unit_count = int(units)
    except (TypeError, ValueError) as exc:
        raise SchedulingError("Academic units must be a whole number of at least 1.") from exc
    if unit_count < 1:
        raise SchedulingError("Academic units must be at least 1.")
    return normalized_code, normalized_title, unit_count


def validate_section_fields(identifier: str, slots_left: int | str) -> tuple[str, int]:
    section_id = identifier.strip()
    if not section_id or section_id.upper() == "TBA":
        raise SchedulingError("Section identifier is required; TBA sections are not accepted.")
    try:
        slots = int(slots_left)
    except (TypeError, ValueError) as exc:
        raise SchedulingError("Available slots must be a whole number of 0 or greater.") from exc
    if slots < 0:
        raise SchedulingError("Available slots cannot be negative.")
    return section_id, slots


def validate_section_meetings(meetings: list[Meeting]) -> None:
    if not meetings:
        raise SchedulingError("Add at least one meeting before saving a section.")
    ordered = sorted(meetings, key=lambda item: item.key)
    for previous, current in zip(ordered, ordered[1:]):
        if previous.day == current.day and previous.end_abs > current.key:
            raise SchedulingError(
                f"Meetings within section {current.section} overlap on {current.day}: "
                f"{previous.start}–{previous.end} and {current.start}–{current.end}."
            )
