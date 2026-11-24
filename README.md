# SchedEase Planner

A Flet-based adaptation of **SchedEase: A Conflict-Free Class Scheduling System** for CPEN60, BSCpE 2-2, Group 7. The interface replaces the proposal's console menu; the required scheduling engine and project scope remain: one in-memory student profile, manually entered data, no accounts, database, network access, or enrollment integration.

## Run the app

### Flet Studio

Open the project in Flet Studio and run the preview. All records are held in memory for the current session and are cleared when the app restarts.

### Run locally

Install Flet on the computer using the official Flet setup instructions, then run the project from its root folder:

```text
flet run src/main.py
```

Python 3.12 or later is specified in `pyproject.toml`. The app has no third-party dependencies beyond Flet.

## Use

1. In **Overview**, set the maximum unit load.
2. In **Subjects**, enter a course and its first section. Add each meeting day/time to the section draft, then save the section. To add more sections to a course, enter the same code/title/units and a different section identifier. Check a subject to pin it.
3. In **Blocked time**, add personal unavailable periods; the periods are inserted into the base BST.
4. In **Recommendations**, run the search. Each result shows total units, campus days, idle gap, chronological meetings, units per subject, and dropped subjects.
5. **System info** summarizes the data structures, algorithms, scope, complexity, and requirement mapping.

Times use 24-hour `HH:MM` input and must fall within 07:00–21:00. Supported days are Monday through Saturday. A class may end exactly when another starts.

## Project structure

```text
src/
  main.py                    Flet page setup and app entry point
  schedule_models.py         Meeting, Section, Subject, Queue state, result records
  schedule_structures.py     Linked Queue and custom BST
  schedule_validation.py     Subject, section, meeting, and interval validation
  scheduler.py               In-memory state, blocked periods, BFS, scoring, Top 3
  views/
    planner.py               Flet input forms and recommendation display
tests/
  test_scheduler.py          unittest verification suite
```

## Requirement-to-implementation mapping

| Requirement | Implementation |
|---|---|
| FR-1 Input validation | `schedule_validation.py`: subject/section fields, meeting format and bounds, duplicate section checks, and section self-overlap validation |
| FR-2 Blocked time | `ScheduleEngine.add_blocked_period()` inserts validated blocked intervals into the base BST |
| FR-3 Subject pinning | `ScheduleEngine.set_pinned()` and pinned-first expansion in `ScheduleEngine.generate()`; pinned subjects have no skip branch |
| FR-4 Conflict detection | `BinarySearchTree.find_overlap()` checks predecessor and successor; conflict reports include the conflicting course/blocker, day, and time |
| FR-5 BFS candidate generation | `LinkedQueue` and `ScheduleEngine.generate()`; full sections, unit-cap overflow, and time conflicts are pruned |
| FR-6 Schedule ranking | `ScheduleEngine._score()` and Top-3 insertion use `(-units, days, idle_gap, discovery_order)` |
| FR-7 Schedule display | `PlannerView._recommendation_control()` displays chronological BST traversal, course metadata, totals, and dropped subjects |
| FR-8 Pinned failure handling | `ScheduleEngine.generate()` reports pinned unit overflow, no-open-section cases, and the failing pinned code when search determines it |

## Data structures

- **Linked Queue:** `QueueNode(state, next)` with `front` and `rear` pointers. `enqueue`, `dequeue`, `peek`, `is_empty`, and FIFO `display` are implemented. Enqueue and dequeue take O(1) time.
- **Subject lookup table:** a Python dictionary keyed by normalized subject code. Each record stores title, units, sections, open-slot counts, and pinned status. Average lookup/insert is O(1).
- **Binary Search Tree:** custom, unbalanced nodes ordered by `day_index * 1440 + start_minute`. Nodes contain start key, absolute end, subject/section labels, meeting display fields, and blocked-period metadata. Insert, predecessor/successor lookup, neighbor overlap detection, in-order traversal, and deep copy are implemented. BST operations are O(h): average O(log n), worst O(n).
- Every queued schedule state has its own BST copy. The proposal pseudocode reuses the parent's BST in an optional-subject skip branch; SchedEase deep-copies that branch too, so later state changes cannot leak between branches.

## Algorithms

### Neighbor-based interval conflict check

For a meeting `[start, end)`, search the BST once for its predecessor (latest key at or before start) and successor (next later key). A conflict exists when the predecessor's end is greater than the new start, or the successor's start is less than the new end. Strict inequalities allow back-to-back meetings. Blocked periods are in the base tree and use the same test. Section meetings are separately validated against one another before storage.

### Queue-based BFS with pruning

Pinned subjects are processed first. Before search, the engine checks for empty subject data, pinned units above the cap, and pinned subjects with no open sections. BFS dequeues each partial state and tries every section for the next course. Full sections, over-cap branches, and BST conflicts are pruned; accepted choices receive an isolated BST copy and are enqueued. Optional subjects also receive a skip branch; pinned subjects never do. If no schedule survives, the engine reports the unplaceable pinned subject when determinable.

### Ranking and Top 3

Every complete schedule is scored and compared by `(-total_units, campus_days, idle_gap_minutes, discovery_order)`. Only the best three are retained. The schedule display traverses meetings chronologically, groups them by day, excludes blocked nodes from the displayed classes and campus-day count, and lists dropped subjects.

## Complexity analysis

Let `k` be the number of subjects, `s` the maximum sections per subject, `m` the maximum meetings in one section, `n` the meeting-node count in a schedule BST, and `h` its height.

| Operation | Time | Extra space |
|---|---:|---:|
| Queue enqueue/dequeue | O(1) | O(1) per node |
| BST insert / predecessor-successor search | O(h), average O(log n), worst O(n) | O(1) iterative search |
| Neighbor overlap check | O(h), average O(log n), worst O(n) | O(1) |
| BST deep copy | O(n) | O(n) copied nodes and O(h) call stack |
| In-order iterator | O(n) | O(h) traversal stack |
| Score one candidate | O(n) | O(h), plus at most six day markers |
| BFS generation, worst case | O((s+1)^k · s · (m·h + n + m·h)) | O((s+1)^k · n) worst-case queued state/tree copies |

The BFS bound includes testing each section's meetings, copying a tree for accepted and skipped branches, and inserting meetings into copied trees. In practice slot, conflict, and unit-cap pruning reduce work, but the search is exponential. A degenerate unbalanced BST has height O(n), so the implementation does not claim guaranteed logarithmic operations.

The proposal's shorter schedule-generation estimate does not include the separate section-meeting count or the cost of copying and inserting into a BST for each branch. The table above accounts for those operations. Enqueue/dequeue themselves remain O(1), excluding construction/copying of the state being enqueued.

## Verification

Run the test suite from the project root:

```text
python -m unittest discover -s tests -v
```

The test suite covers the proposal's S-1–S-7 scenario and the required edge cases. **Execution status for this delivery: NOT RUN.** The Flet Studio preview was unavailable during this turn, and no standalone Python execution tool is available here. No test is marked PASS without execution; use the command above to produce the actual run results.

| Test ID | Input/procedure | Expected result | Actual result | Status |
|---|---|---|---|---|
| TC-01 | Add CPEN65 with two sections (S-2) | Both sections stored under one subject | Not run; preview unavailable | NOT RUN |
| TC-02 | TBA/missing meeting time | Rejected with descriptive validation error | Not run; preview unavailable | NOT RUN |
| TC-03 | End before/equal start; out-of-range time; Sunday | Rejected; no invalid record stored | Not run; preview unavailable | NOT RUN |
| TC-04 | Duplicate section S-7; negative slots | Rejected; existing record unchanged | Not run; preview unavailable | NOT RUN |
| TC-05 | Overlapping meetings within one section | Section rejected | Not run; preview unavailable | NOT RUN |
| TC-06 | Block Mon 07:00–10:00, then add Mon 08:00–11:00 class | Conflict reports BLOCKED and its day/time | Not run; preview unavailable | NOT RUN |
| TC-07 | Tuesday 09:00–12:00 then Tuesday 12:00–13:00 | BST allows back-to-back; traversal remains chronological | Not run; preview unavailable | NOT RUN |
| TC-08 | Optional section with zero slots | Section pruned; optional course may be dropped | Not run; preview unavailable | NOT RUN |
| TC-09 | Pin CPEN65 and generate | Every recommendation contains CPEN65 | Not run; preview unavailable | NOT RUN |
| TC-10 | Pin a subject whose sections all have zero slots | Controlled error names the pinned course | Not run; preview unavailable | NOT RUN |
| TC-11 | Pin two 3-unit subjects with a 5-unit cap | Controlled pinned-unit-limit error | Not run; preview unavailable | NOT RUN |
| TC-12 | Add a 9-unit course with a 9-unit cap | Boundary accepted; 9-unit schedule can be recommended | Not run; preview unavailable | NOT RUN |
| TC-13 | Run proposal sample S-1–S-5 | Top ranks are (9 units, 2 days, 0 gap), (9, 3, 0), (7, 2, 0) | Not run; preview unavailable | NOT RUN |
| TC-14 | Generate before adding subjects | “No course data has been entered yet”; no crash | Not run; preview unavailable | NOT RUN |
| TC-15 | Eight subjects × three sections, one full section per subject | Search completes and retains at most three ranked schedules | Not run; preview unavailable | NOT RUN |
| TC-16 | Copy a schedule BST and extend the copy | Base tree remains unchanged | Not run; preview unavailable | NOT RUN |
| TC-17 | Queue enqueue/dequeue/peek/display | FIFO order and empty handling work | Not run; preview unavailable | NOT RUN |
| TC-18 | BST predecessor/successor/in-order checks | Correct neighbors and chronological traversal | Not run; preview unavailable | NOT RUN |
| TC-19 | Configure maximum units as 0 or malformed text | Controlled `SchedulingError`; no crash | Not run; preview unavailable | NOT RUN |

### Proposal reference output (not a runtime capture)

For S-1–S-5, the proposal's expected ranking is:

```text
SCHEDULE RECOMMENDATION #1 — 9/9 units, 2 days, 0 min gap
Tuesday  10:00 AM–01:00 PM | CPEN125 | Section 4-1
Wednesday 09:00 AM–12:00 PM | CPEN65 | Section 2-2
Wednesday 12:00 PM–03:00 PM | CPEN135 | Section 4-1
Dropped: CPEN111

SCHEDULE RECOMMENDATION #2 — 9/9 units, 3 days, 0 min gap
Tuesday  10:00 AM–01:00 PM | CPEN125 | Section 4-1
Wednesday 09:00 AM–12:00 PM | CPEN65 | Section 2-2
Thursday  08:00 AM–11:00 AM | CPEN135 | Section 4-2
Dropped: CPEN111

SCHEDULE RECOMMENDATION #3 — 7/9 units, 2 days, 0 min gap
Wednesday 09:00 AM–12:00 PM | CPEN65 | Section 2-2
Wednesday 12:00 PM–03:00 PM | CPEN135 | Section 4-1
Friday    01:00 PM–02:00 PM | CPEN111 | Section 4-1
Dropped: CPEN125
```

This reference is derived from the proposal's sample operation trace; it is not presented as an executed screenshot or test result. No database, network services, authentication, instructor/room conflict checks, prerequisites, or official enrollment actions are implemented.
