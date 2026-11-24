"""SchedEase application state, conflict checks, BFS generation, and ranking."""

from __future__ import annotations

from schedule_models import (
    GenerationResult,
    Meeting,
    ScheduleRecommendation,
    ScheduleState,
    SchedulingError,
    Section,
    Subject,
)
from schedule_structures import BinarySearchTree, LinkedQueue
from schedule_validation import (
    validate_meeting,
    validate_section_fields,
    validate_section_meetings,
    validate_subject_fields,
)


class ScheduleEngine:
    """In-memory planner. The dictionary is keyed by normalized subject code."""

    def __init__(self, max_units: int | str = 21):
        self.max_units = 21
        self.set_max_units(max_units)
        self.subjects: dict[str, Subject] = {}
        self.base_tree = BinarySearchTree()
        self.last_result = GenerationResult()

    def set_max_units(self, value: int | str) -> None:
        try:
            maximum = int(value)
        except (TypeError, ValueError) as exc:
            raise SchedulingError("Maximum units must be a whole number of at least 1.") from exc
        if maximum < 1:
            raise SchedulingError("Maximum units must be at least 1.")
        self.max_units = maximum

    def add_section(
        self,
        code: str,
        title: str,
        units: int | str,
        section_identifier: str,
        slots_left: int | str,
        meetings: list[tuple[str, str, str]],
    ) -> Subject:
        normalized_code, normalized_title, unit_count = validate_subject_fields(code, title, units)
        section_id, slots = validate_section_fields(section_identifier, slots_left)
        if normalized_code in self.subjects:
            subject = self.subjects[normalized_code]
            if subject.title != normalized_title or subject.units != unit_count:
                raise SchedulingError(
                    f"{normalized_code} already exists with title '{subject.title}' and "
                    f"{subject.units} units; additional sections must match those details."
                )
            if any(section.identifier.casefold() == section_id.casefold() for section in subject.sections):
                raise SchedulingError(f"Section '{section_id}' already exists for {normalized_code}.")
        else:
            subject = Subject(normalized_code, normalized_title, unit_count)

        records = [
            validate_meeting(day, start, end, normalized_code, normalized_title, section_id)
            for day, start, end in meetings
        ]
        validate_section_meetings(records)
        section = Section(section_id, slots, records)
        if normalized_code not in self.subjects:
            self.subjects[normalized_code] = subject
        subject.sections.append(section)
        return subject

    def add_blocked_period(self, day: str, start: str, end: str, reason: str) -> Meeting:
        label = reason.strip()
        if not label:
            raise SchedulingError("Enter a short reason for the blocked period.")
        meeting = validate_meeting(
            day,
            start,
            end,
            "BLOCKED",
            "Blocked time",
            "BLOCKED",
            blocked=True,
            reason=label,
        )
        conflict = self.base_tree.find_overlap(meeting)
        if conflict is not None:
            raise SchedulingError(
                f"Blocked period overlaps existing blocked time on {conflict.day} "
                f"{conflict.start}–{conflict.end} ({conflict.reason})."
            )
        self.base_tree.insert(meeting)
        return meeting

    def set_pinned(self, subject_code: str, pinned: bool) -> None:
        code = subject_code.strip().upper()
        subject = self.subjects.get(code)
        if subject is None:
            raise SchedulingError(f"Subject {code or '(blank)'} was not found.")
        subject.pinned = bool(pinned)

    def _describe_conflict(self, node) -> str:
        label = f"blocked period '{node.reason}'" if node.blocked else f"{node.subject_code} section {node.section}"
        return f"{label} on {node.day} {node.start}–{node.end}"

    def _score(self, state: ScheduleState, discovery_order: int) -> ScheduleRecommendation:
        days: set[int] = set()
        idle_gap = 0
        previous = None
        for node in state.tree.iter_inorder():
            if node.blocked:
                continue
            day_index = node.key // 1440
            days.add(day_index)
            if previous is not None and day_index == previous.key // 1440:
                idle_gap += max(0, node.key - previous.end_abs)
            previous = node
        return ScheduleRecommendation(state, len(days), idle_gap, discovery_order)

    def generate(self) -> GenerationResult:
        result = GenerationResult()
        self.last_result = result
        if not self.subjects:
            result.error = "No course data has been entered yet. Add a subject and section first."
            return result

        all_subjects = list(self.subjects.values())
        pinned = [subject for subject in all_subjects if subject.pinned]
        pinned_units = sum(subject.units for subject in pinned)
        if pinned_units > self.max_units:
            result.error = (
                f"Pinned subjects total {pinned_units} units, exceeding the "
                f"{self.max_units}-unit maximum."
            )
            return result
        for subject in pinned:
            if not any(section.slots_left > 0 for section in subject.sections):
                result.error = f"Pinned subject {subject.code} has no section with available slots."
                return result

        ordered_subjects = pinned + [subject for subject in all_subjects if not subject.pinned]
        queue: LinkedQueue[ScheduleState] = LinkedQueue()
        queue.enqueue(ScheduleState(0, [], 0, self.base_tree.deep_copy()))
        pin_failures: dict[str, list[str]] = {}
        discovery_order = 0

        while not queue.is_empty():
            state = queue.dequeue()
            result.states_processed += 1
            if state.next_subject_index == len(ordered_subjects):
                result.complete_candidates += 1
                discovery_order += 1
                candidate = self._score(state, discovery_order)
                result.recommendations.append(candidate)
                result.recommendations.sort(key=lambda item: item.rank_key)
                if len(result.recommendations) > 3:
                    result.recommendations.pop()
                continue

            subject = ordered_subjects[state.next_subject_index]
            placed_any = False
            section_failure_reasons: list[str] = []
            for section in subject.sections:
                if section.slots_left == 0:
                    result.full_section_rejections += 1
                    section_failure_reasons.append(f"section {section.identifier} has no open slots")
                    continue
                if state.units + subject.units > self.max_units:
                    result.unit_cap_rejections += 1
                    section_failure_reasons.append("adding it would exceed the unit maximum")
                    continue

                conflict_description = None
                conflict_meeting = None
                for meeting in section.meetings:
                    conflict = state.tree.find_overlap(meeting)
                    if conflict is not None:
                        result.conflict_rejections += 1
                        conflict_description = self._describe_conflict(conflict)
                        conflict_meeting = meeting
                        break
                if conflict_description is not None:
                    detail = (
                        f"{subject.code} section {section.identifier} "
                        f"({conflict_meeting.day} {conflict_meeting.start}–{conflict_meeting.end}) "
                        f"conflicts with {conflict_description}"
                    )
                    if detail not in result.conflict_details and len(result.conflict_details) < 12:
                        result.conflict_details.append(detail)
                    section_failure_reasons.append(conflict_description)
                    continue

                branch_tree = state.tree.deep_copy()
                for meeting in section.meetings:
                    branch_tree.insert(meeting)
                queue.enqueue(
                    ScheduleState(
                        state.next_subject_index + 1,
                        state.selected_sections + [(subject.code, section)],
                        state.units + subject.units,
                        branch_tree,
                    )
                )
                placed_any = True

            if not subject.pinned:
                # A skip branch owns a deep copy too; schedule states never share mutable BSTs.
                queue.enqueue(
                    ScheduleState(
                        state.next_subject_index + 1,
                        list(state.selected_sections),
                        state.units,
                        state.tree.deep_copy(),
                    )
                )
            elif not placed_any:
                pin_failures.setdefault(subject.code, []).extend(section_failure_reasons)

        if not result.recommendations and pinned:
            failed_code = next((subject.code for subject in pinned if subject.code in pin_failures), pinned[-1].code)
            reasons = list(dict.fromkeys(pin_failures.get(failed_code, [])))
            detail = "; ".join(reasons[:3])
            result.error = f"No conflict-free schedule can include all pinned subjects. Unplaceable pinned subject: {failed_code}."
            if detail:
                result.error += f" Reason(s): {detail}."
        elif not result.recommendations:
            result.error = "No valid schedule could be generated. Check section availability and meeting data."
        return result
