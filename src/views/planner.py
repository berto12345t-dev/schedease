"""Polished Flet interface for entering schedule data and viewing recommendations."""

from __future__ import annotations

import logging

import flet as ft

from schedule_models import DAYS, SchedulingError, format_time
from schedule_validation import validate_meeting, validate_section_meetings
from scheduler import ScheduleEngine

log = logging.getLogger("app.views.planner")

INK = ft.Colors.BLUE_GREY_900
MUTED = ft.Colors.BLUE_GREY_600
CANVAS = ft.Colors.BLUE_50
BORDER = ft.Colors.BLUE_100
ACCENT = ft.Colors.BLUE_700
ACCENT_LIGHT = ft.Colors.BLUE_50
WHITE = ft.Colors.WHITE


class PlannerView:
    def __init__(self, page: ft.Page):
        self.page = page
        self.engine = ScheduleEngine()
        self.meeting_draft: list[tuple[str, str, str]] = []

        self.status = ft.Text("", color=MUTED, size=13)
        self.status_card = ft.Container(
            visible=False,
            padding=ft.Padding.symmetric(horizontal=14, vertical=10),
            bgcolor=WHITE,
            border_radius=ft.BorderRadius.all(12),
            content=self.status,
        )
        self.subject_list = ft.Column(
            spacing=10,
            controls=[ft.Text("No courses yet. Add a section above to get started.", color=MUTED, size=13)],
        )
        self.blocked_list = ft.Column(
            spacing=10,
            controls=[ft.Text("No blocked periods have been added.", color=MUTED, size=13)],
        )
        self.draft_list = ft.Column(spacing=6)
        self.results = ft.Column(spacing=14)
        self.stats = ft.Text("Run the search to see how many states and candidates were evaluated.", color=MUTED)

        self.max_units = self._field("Maximum academic units", value="21", keyboard_type=ft.KeyboardType.NUMBER)
        self.code = self._field("Subject code", hint_text="e.g. CPEN65")
        self.title = self._field("Course title", hint_text="e.g. Data Structures")
        self.units = self._field("Academic units", keyboard_type=ft.KeyboardType.NUMBER)
        self.section = self._field("Section identifier", hint_text="e.g. 2-1")
        self.slots = self._field("Open slots", keyboard_type=ft.KeyboardType.NUMBER)
        self.meeting_day = self._day_dropdown()
        self.meeting_start = self._field("Start time", value="09:00", hint_text="24-hour HH:MM")
        self.meeting_end = self._field("End time", value="12:00", hint_text="24-hour HH:MM")

        self.block_day = self._day_dropdown()
        self.block_start = self._field("Start time", value="09:00", hint_text="24-hour HH:MM")
        self.block_end = self._field("End time", value="10:00", hint_text="24-hour HH:MM")
        self.block_reason = self._field("What is this time for?", hint_text="e.g. Work, commute, personal")

        self.kpi_values = {
            "units": ft.Text("21", size=24, weight=ft.FontWeight.BOLD, color=INK),
            "courses": ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=INK),
            "pinned": ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=INK),
            "blocked": ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=INK),
        }

        self.navigation = [
            ("Overview", ft.Icons.CALENDAR_TODAY),
            ("Subjects", ft.Icons.SCHOOL),
            ("Blocked time", ft.Icons.EVENT_BUSY),
            ("Recommendations", ft.Icons.SCHEDULE),
            ("About", ft.Icons.INFO),
        ]
        self.current_page = 0
        self.screen_title = ft.Text("Overview", size=18, weight=ft.FontWeight.BOLD, color=WHITE)
        self.screens = [
            self._overview_tab(),
            self._subjects_tab(),
            self._blocked_tab(),
            self._recommendations_tab(),
            self._system_info_tab(),
        ]
        for index, screen in enumerate(self.screens):
            screen.visible = index == 0
        self.nav_items = ft.Column(spacing=4)
        self._refresh_navigation()

    @staticmethod
    def _field(label: str, **kwargs) -> ft.TextField:
        return ft.TextField(
            label=label,
            filled=True,
            fill_color=ft.Colors.BLUE_50,
            border={
                ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                    border_radius=12, side=ft.BorderSide(1, BORDER)),
                ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                    border_radius=12, side=ft.BorderSide(2, ACCENT)),
            },
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=13),
            **kwargs,
        )

    @staticmethod
    def _day_dropdown() -> ft.Dropdown:
        return ft.Dropdown(
            label="Day",
            value="Monday",
            options=[ft.DropdownOption(text=day) for day in DAYS],
            filled=True,
            fill_color=ft.Colors.BLUE_50,
            border={
                ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                    border_radius=12, side=ft.BorderSide(1, BORDER)),
                ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                    border_radius=12, side=ft.BorderSide(2, ACCENT)),
            },
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=13),
        )

    @staticmethod
    def _card(content: ft.Control, *, padding: int = 20, bgcolor=WHITE) -> ft.Container:
        return ft.Container(
            padding=padding,
            bgcolor=bgcolor,
            border=ft.Border.all(1, BORDER),
            border_radius=ft.BorderRadius.all(18),
            content=content,
        )

    @staticmethod
    def _primary_button(label: str, icon, on_click) -> ft.Button:
        return ft.Button(
            content=ft.Row(
                tight=True,
                spacing=9,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[ft.Icon(icon, size=18, color=WHITE), ft.Text(label, weight=ft.FontWeight.W_600)],
            ),
            bgcolor=ACCENT,
            color=WHITE,
            style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=18, vertical=13)),
            on_click=on_click,
        )

    @staticmethod
    def _intro(icon, title: str, subtitle: str) -> ft.Control:
        return ft.Row(
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Container(
                    width=46,
                    height=46,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=ACCENT_LIGHT,
                    border_radius=ft.BorderRadius.all(14),
                    content=ft.Icon(icon, color=ACCENT, size=23),
                ),
                ft.Column(
                    expand=True,
                    tight=True,
                    spacing=3,
                    controls=[
                        ft.Text(title, size=21, weight=ft.FontWeight.BOLD, color=INK),
                        ft.Text(subtitle, size=13, color=MUTED),
                    ],
                ),
            ],
        )

    def _refresh_navigation(self) -> None:
        self.nav_items.controls = [
            ft.Container(
                border_radius=ft.BorderRadius.all(12),
                bgcolor=ACCENT_LIGHT if index == self.current_page else WHITE,
                content=ft.ListTile(
                    leading=ft.Icon(icon, color=ACCENT if index == self.current_page else MUTED),
                    title=ft.Text(label, color=ACCENT if index == self.current_page else INK,
                                  weight=ft.FontWeight.W_600 if index == self.current_page else ft.FontWeight.NORMAL),
                    on_click=lambda e, selected=index: self._navigate(selected),
                ),
            )
            for index, (label, icon) in enumerate(self.navigation)
        ]

    def _navigate(self, index: int) -> None:
        self.current_page = index
        self.screen_title.value = self.navigation[index][0]
        for screen_index, screen in enumerate(self.screens):
            screen.visible = screen_index == index
        self._refresh_navigation()
        self._toggle_sidebar(False)

    def _toggle_sidebar(self, is_open: bool) -> None:
        self.sidebar_scrim.visible = is_open
        self.sidebar.visible = is_open
        self.page.update()

    def build(self) -> ft.Control:
        header = ft.Container(
            bgcolor=ACCENT,
            padding=ft.Padding.symmetric(horizontal=10, vertical=8),
            content=ft.Row(
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(ft.Icons.MENU, icon_color=WHITE, tooltip="Open navigation",
                                  on_click=lambda: self._toggle_sidebar(True)),
                    ft.Column(expand=True, tight=True, spacing=1, controls=[
                        ft.Text("SCHEDEASE", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_100),
                        self.screen_title,
                    ]),
                    ft.Container(
                        padding=8, bgcolor=ft.Colors.with_opacity(0.16, WHITE),
                        border_radius=ft.BorderRadius.all(12),
                        content=ft.Icon(ft.Icons.CALENDAR_MONTH, color=WHITE, size=22),
                    ),
                ],
            ),
        )
        content = ft.Column(
            expand=True,
            spacing=0,
            controls=[
                header,
                ft.Container(
                    expand=True,
                    alignment=ft.Alignment.TOP_CENTER,
                    padding=ft.Padding.symmetric(horizontal=16),
                    content=ft.Container(
                        width=920,
                        content=ft.Column(expand=True, spacing=0, controls=[
                            ft.Container(content=self.status_card),
                            ft.Column(expand=True, spacing=0, controls=self.screens),
                        ]),
                    ),
                ),
            ],
        )
        self.sidebar_scrim = ft.Container(
            left=0, top=0, right=0, bottom=0, visible=False,
            bgcolor=ft.Colors.with_opacity(0.42, ft.Colors.BLACK),
            on_click=lambda: self._toggle_sidebar(False),
        )
        self.sidebar = ft.Container(
            left=0, top=0, bottom=0, width=280, visible=False, bgcolor=WHITE,
            padding=ft.Padding.symmetric(horizontal=16, vertical=20),
            content=ft.Column(expand=True, spacing=18, controls=[
                ft.Row(spacing=12, controls=[
                    ft.Container(width=46, height=46, bgcolor=ACCENT,
                                 border_radius=ft.BorderRadius.all(14), alignment=ft.Alignment.CENTER,
                                 content=ft.Icon(ft.Icons.CALENDAR_MONTH, color=WHITE, size=25)),
                    ft.Column(expand=True, tight=True, spacing=2, controls=[
                        ft.Text("SchedEase", size=20, weight=ft.FontWeight.BOLD, color=INK),
                        ft.Text("CLASS SCHEDULING", size=10, color=MUTED),
                    ]),
                    ft.IconButton(ft.Icons.CLOSE, icon_color=MUTED, tooltip="Close navigation",
                                  on_click=lambda: self._toggle_sidebar(False)),
                ]),
                ft.Divider(color=BORDER),
                ft.Text("PLAN YOUR SEMESTER", size=10, weight=ft.FontWeight.BOLD, color=MUTED),
                self.nav_items,
                ft.Container(expand=True),
                ft.Text("Private · Session only", size=12, color=MUTED),
            ]),
        )
        return ft.SafeArea(expand=True, content=ft.Stack(expand=True, controls=[
            ft.Container(left=0, top=0, right=0, bottom=0, content=content),
            self.sidebar_scrim,
            self.sidebar,
        ]))

    def _overview_tab(self) -> ft.Control:
        kpis = ft.ResponsiveRow(
            spacing=12,
            run_spacing=12,
            controls=[
                self._kpi_card("Unit cap", self.kpi_values["units"], ft.Icons.BAR_CHART, {"xs": 6, "md": 3}),
                self._kpi_card("Subjects", self.kpi_values["courses"], ft.Icons.SCHOOL, {"xs": 6, "md": 3}),
                self._kpi_card("Pinned", self.kpi_values["pinned"], ft.Icons.PUSH_PIN, {"xs": 6, "md": 3}),
                self._kpi_card("Blocked periods", self.kpi_values["blocked"], ft.Icons.EVENT_BUSY, {"xs": 6, "md": 3}),
            ],
        )
        workflow = self._card(
            ft.Column(
                spacing=13,
                controls=[
                    ft.Text("A simple planning flow", size=17, weight=ft.FontWeight.BOLD, color=INK),
                    self._step_row("01", "Add your courses", "Enter each available section, meeting time, and open slot count."),
                    self._step_row("02", "Set your constraints", "Add blocked periods and pin courses you must take."),
                    self._step_row("03", "Compare schedules", "Generate up to three options ranked by units, campus days, and idle time."),
                ],
            )
        )
        callout = self._card(
            ft.Column(
                spacing=10,
                controls=[
                    ft.Row(spacing=9, controls=[ft.Icon(ft.Icons.INFO_OUTLINE, color=ACCENT), ft.Text("Planning note", size=16, weight=ft.FontWeight.BOLD, color=INK)]),
                    ft.Text("SchedEase is an advisory planner. Confirm your final course load with your academic adviser and the official enrollment portal.", color=MUTED, size=13),
                    ft.Text("Class window: Monday–Saturday · 07:00–21:00 · Data stays in memory for this session.", color=INK, size=12, weight=ft.FontWeight.W_500),
                ],
            ),
            bgcolor=ACCENT_LIGHT,
        )
        return ft.Container(
            expand=True,
            padding=ft.Padding.only(top=20, bottom=10, left=2, right=2),
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=18,
                controls=[
                    self._overview_hero(),
                    ft.Row(controls=[
                        ft.Text("Your planning snapshot", size=17, weight=ft.FontWeight.BOLD, color=INK, expand=True),
                        ft.Text("THIS SESSION", size=10, weight=ft.FontWeight.W_600, color=MUTED),
                    ]),
                    kpis,
                    self._card(ft.Row(spacing=12, controls=[
                        ft.Container(width=42, height=42, bgcolor=ACCENT_LIGHT,
                                     border_radius=ft.BorderRadius.all(12), alignment=ft.Alignment.CENTER,
                                     content=ft.Icon(ft.Icons.EVENT_AVAILABLE, color=ACCENT, size=22)),
                        ft.Column(expand=True, tight=True, spacing=3, controls=[
                            ft.Text("Find your best fit", weight=ft.FontWeight.BOLD, color=INK),
                            ft.Text("Compare up to three schedules", size=12, color=MUTED),
                        ]),
                        ft.IconButton(ft.Icons.ARROW_FORWARD, icon_color=ACCENT,
                                      tooltip="View recommendations", on_click=lambda: self._navigate(3)),
                    ]), padding=14),
                    self._card(ft.Column(spacing=12, controls=[
                        ft.Text("Academic unit limit", size=16, weight=ft.FontWeight.BOLD, color=INK),
                        ft.Text("Set the maximum units allowed for this semester.", size=12, color=MUTED),
                        self.max_units,
                        self._primary_button("Save unit limit", ft.Icons.SAVE, self._save_max_units),
                    ])),
                    ft.ResponsiveRow(
                        spacing=14,
                        run_spacing=14,
                        controls=[
                            ft.Container(col={"xs": 12, "md": 7}, content=workflow),
                            ft.Container(col={"xs": 12, "md": 5}, content=callout),
                        ],
                    ),
                ],
            ),
        )

    def _overview_hero(self) -> ft.Control:
        # A small calendar illustration is decorative, not a generated schedule.
        calendar = ft.Container(
            width=76, padding=8, bgcolor=WHITE, border_radius=ft.BorderRadius.all(14),
            content=ft.Column(tight=True, spacing=5, controls=[
                ft.Container(height=8, bgcolor=ft.Colors.BLUE_300, border_radius=ft.BorderRadius.all(4)),
                *[ft.Row(spacing=4, controls=[
                    ft.Container(width=16, height=14, border_radius=ft.BorderRadius.all(4),
                                 bgcolor=color) for color in row
                ]) for row in [
                    (ft.Colors.BLUE_50, ft.Colors.LIGHT_GREEN_300, ft.Colors.BLUE_50),
                    (ft.Colors.BLUE_300, ft.Colors.BLUE_50, ft.Colors.AMBER_300),
                    (ft.Colors.BLUE_50, ft.Colors.PURPLE_200, ft.Colors.BLUE_50),
                ]],
            ]),
        )
        return ft.Container(
            padding=20, bgcolor=ft.Colors.BLUE_600, border_radius=ft.BorderRadius.all(20),
            content=ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Column(expand=True, tight=True, spacing=9, controls=[
                    ft.Text("PLAN WITH CONFIDENCE", size=10, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_100),
                    ft.Text("A better week starts here.", size=22, weight=ft.FontWeight.BOLD, color=WHITE),
                    ft.Text("Build a schedule that fits your life.", size=12, color=WHITE),
                    ft.TextButton("Add a subject", icon=ft.Icons.ADD,
                                  style=ft.ButtonStyle(color=WHITE, padding=0),
                                  on_click=lambda: self._navigate(1)),
                ]),
                calendar,
            ]),
        )

    def _kpi_card(self, label: str, value: ft.Text, icon, col) -> ft.Container:
        return ft.Container(
            col=col,
            padding=16,
            bgcolor=WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=ft.BorderRadius.all(16),
            content=ft.Column(
                tight=True, spacing=8,
                controls=[
                    ft.Container(
                        width=34, height=34, alignment=ft.Alignment.CENTER,
                        bgcolor=ACCENT_LIGHT, border_radius=ft.BorderRadius.all(10),
                        content=ft.Icon(icon, size=18, color=ACCENT),
                    ),
                    value,
                    ft.Text(label, size=11, color=MUTED),
                ],
            ),
        )

    @staticmethod
    def _step_row(number: str, title: str, detail: str) -> ft.Control:
        return ft.Row(
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                ft.Container(
                    width=34,
                    height=34,
                    alignment=ft.Alignment.CENTER,
                    bgcolor=ACCENT_LIGHT,
                    border_radius=ft.BorderRadius.all(11),
                    content=ft.Text(number, size=11, weight=ft.FontWeight.BOLD, color=ACCENT),
                ),
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(title, weight=ft.FontWeight.W_600, color=INK),
                        ft.Text(detail, size=12, color=MUTED),
                    ],
                ),
            ],
        )

    def _subjects_tab(self) -> ft.Control:
        form = self._card(
            ft.Column(
                spacing=14,
                controls=[
                    ft.Text("Course details", size=16, weight=ft.FontWeight.BOLD, color=INK),
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=8,
                        controls=[
                            ft.Container(col={"xs": 12, "md": 4}, content=self.code),
                            ft.Container(col={"xs": 12, "md": 5}, content=self.title),
                            ft.Container(col={"xs": 12, "md": 3}, content=self.units),
                            ft.Container(col={"xs": 12, "md": 6}, content=self.section),
                            ft.Container(col={"xs": 12, "md": 6}, content=self.slots),
                        ],
                    ),
                    ft.Divider(color=BORDER),
                    ft.Text("Section meeting times", size=16, weight=ft.FontWeight.BOLD, color=INK),
                    ft.Text("Add every weekly meeting for this section before saving it.", size=12, color=MUTED),
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=8,
                        controls=[
                            ft.Container(col={"xs": 12, "md": 4}, content=self.meeting_day),
                            ft.Container(col={"xs": 6, "md": 4}, content=self.meeting_start),
                            ft.Container(col={"xs": 6, "md": 4}, content=self.meeting_end),
                        ],
                    ),
                    ft.Row(wrap=True, spacing=10, controls=[self._primary_button("Add meeting", ft.Icons.ADD, self._add_draft_meeting)]),
                    self.draft_list,
                    ft.Row(wrap=True, controls=[self._primary_button("Save section", ft.Icons.SAVE, self._save_section)]),
                ],
            )
        )
        return ft.Container(
            expand=True,
            padding=ft.Padding.only(top=20, bottom=10, left=2, right=2),
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=16,
                controls=[
                    self._intro(ft.Icons.SCHOOL, "Courses and sections", "One course can have several section choices."),
                    form,
                    self._card(
                        ft.Column(
                            spacing=12,
                            controls=[
                                ft.Text("Your course list", size=16, weight=ft.FontWeight.BOLD, color=INK),
                                ft.Text("Pin courses to require them in every plan", size=12, color=MUTED),
                                self.subject_list,
                            ],
                        )
                    ),
                ],
            ),
        )

    def _blocked_tab(self) -> ft.Control:
        form = self._card(
            ft.Column(
                spacing=14,
                controls=[
                    ft.Text("When are you unavailable?", size=16, weight=ft.FontWeight.BOLD, color=INK),
                    ft.Text("Blocked periods are treated as occupied time by the conflict checker.", size=12, color=MUTED),
                    ft.ResponsiveRow(
                        spacing=12,
                        run_spacing=8,
                        controls=[
                            ft.Container(col={"xs": 12, "md": 4}, content=self.block_day),
                            ft.Container(col={"xs": 6, "md": 4}, content=self.block_start),
                            ft.Container(col={"xs": 6, "md": 4}, content=self.block_end),
                            ft.Container(col={"xs": 12, "md": 8}, content=self.block_reason),
                            ft.Container(col={"xs": 12, "md": 4}, content=self._primary_button("Add blocked time", ft.Icons.EVENT_BUSY, self._add_blocked)),
                        ],
                    ),
                ],
            )
        )
        return ft.Container(
            expand=True,
            padding=ft.Padding.only(top=20, bottom=10, left=2, right=2),
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=16,
                controls=[
                    self._intro(ft.Icons.EVENT_BUSY, "Protect your personal time", "Add periods that must remain free of classes."),
                    form,
                    self._card(
                        ft.Column(
                            spacing=12,
                            controls=[ft.Text("Blocked periods", size=16, weight=ft.FontWeight.BOLD, color=INK), self.blocked_list],
                        )
                    ),
                ],
            ),
        )

    def _recommendations_tab(self) -> ft.Control:
        empty = self._empty_state(
            ft.Icons.CALENDAR_MONTH,
            "Your schedule options will appear here",
            "Add your courses and constraints, then generate recommendations.",
        )
        self.results.controls = [empty]
        return ft.Container(
            expand=True,
            padding=ft.Padding.only(top=20, bottom=10, left=2, right=2),
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=16,
                controls=[
                    self._intro(ft.Icons.SCHEDULE, "Recommended schedules", "Ranked by units, campus days, then idle gap."),
                    self._card(
                        ft.ResponsiveRow(
                            spacing=14,
                            run_spacing=10,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Container(
                                    col={"xs": 12, "md": 8},
                                    content=ft.Column(
                                        tight=True,
                                        spacing=4,
                                        controls=[
                                            ft.Text("Ready to compare your options?", size=16, weight=ft.FontWeight.BOLD, color=INK),
                                            ft.Text("The search keeps all pinned courses and excludes full, over-cap, or conflicting choices.", size=12, color=MUTED),
                                        ],
                                    ),
                                ),
                                ft.Container(
                                    col={"xs": 12, "md": 4},
                                    content=ft.Row(
                                        alignment=ft.MainAxisAlignment.END,
                                        controls=[self._primary_button("Generate schedules", ft.Icons.AUTO_AWESOME, self._generate)],
                                    ),
                                ),
                            ],
                        )
                    ),
                    self._card(self.stats, padding=14, bgcolor=CANVAS),
                    self.results,
                ],
            ),
        )

    def _system_info_tab(self) -> ft.Control:
        sections = [
            ("Core structures", "A linked FIFO Queue expands schedule states level by level. A custom unbalanced BST stores blocked times and selected class meetings. A dictionary keyed by subject code provides subject lookup."),
            ("Search and ranking", "Pinned subjects are placed first and never skipped. BFS prunes full sections, conflicts, and unit-cap violations. Complete schedules are ranked by highest units, fewest campus days, least idle gap, then discovery order."),
            ("Scope", "One student profile per session; in-memory only. No database, network, login, instructor or room conflict checks, prerequisite validation, or enrollment integration."),
            ("Complexity", "Queue enqueue/dequeue O(1). BST operations are O(h), average O(log n), worst O(n). Copying a tree costs O(n). Candidate search is exponential in the number of subjects and section options; scoring one schedule is O(n)."),
            ("Proposal interpretation", "Blocked BST nodes are excluded from campus-day and idle-gap scoring, matching the proposal's scoring pseudocode. Optional skip branches also receive isolated BST copies so branches cannot mutate shared state."),
        ]
        return ft.Container(
            expand=True,
            padding=ft.Padding.only(top=20, bottom=10, left=2, right=2),
            content=ft.Column(
                expand=True,
                scroll=ft.ScrollMode.AUTO,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                spacing=14,
                controls=[
                    self._intro(ft.Icons.INFO, "How SchedEase works", "The algorithms and constraints behind your recommendations."),
                    *[
                        self._card(
                            ft.Column(
                                spacing=6,
                                controls=[
                                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=INK),
                                    ft.Text(detail, color=MUTED, size=13),
                                ],
                            )
                        )
                        for title, detail in sections
                    ],
                ],
            ),
        )

    @staticmethod
    def _empty_state(icon, title: str, description: str) -> ft.Control:
        return ft.Container(
            padding=30,
            bgcolor=WHITE,
            border=ft.Border.all(1, BORDER),
            border_radius=ft.BorderRadius.all(18),
            content=ft.Column(
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
                controls=[
                    ft.Icon(icon, size=34, color=ACCENT),
                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD, color=INK, text_align=ft.TextAlign.CENTER),
                    ft.Text(description, size=13, color=MUTED, text_align=ft.TextAlign.CENTER),
                ],
            ),
        )

    def _show_status(self, message: str, *, error: bool = False) -> None:
        self.status.value = message
        self.status_card.visible = True
        self.status.color = ft.Colors.RED_800 if error else ACCENT
        self.status_card.bgcolor = ft.Colors.RED_50 if error else ACCENT_LIGHT
        self.status_card.border = ft.Border.all(1, ft.Colors.RED_100 if error else ft.Colors.BLUE_100)
        self.page.update()

    def _refresh_dashboard(self) -> None:
        self.kpi_values["units"].value = str(self.engine.max_units)
        self.kpi_values["courses"].value = str(len(self.engine.subjects))
        self.kpi_values["pinned"].value = str(sum(subject.pinned for subject in self.engine.subjects.values()))
        self.kpi_values["blocked"].value = str(sum(node.blocked for node in self.engine.base_tree.iter_inorder()))

    def _save_max_units(self) -> None:
        try:
            self.engine.set_max_units(self.max_units.value or "")
        except SchedulingError as exc:
            self._show_status(str(exc), error=True)
            return
        self._refresh_dashboard()
        self._show_status(f"Maximum unit limit set to {self.engine.max_units}.")

    def _add_draft_meeting(self) -> None:
        try:
            section_id = (self.section.value or "").strip()
            code = (self.code.value or "").strip().upper()
            title = (self.title.value or "").strip()
            if not section_id or not code or not title:
                raise SchedulingError("Enter the subject code, course title, and section identifier first.")
            meeting = validate_meeting(
                self.meeting_day.value or "",
                self.meeting_start.value or "",
                self.meeting_end.value or "",
                code,
                title,
                section_id,
            )
            trial = [
                validate_meeting(day, start, end, code, title, section_id)
                for day, start, end in self.meeting_draft
            ] + [meeting]
            validate_section_meetings(trial)
        except SchedulingError as exc:
            self._show_status(str(exc), error=True)
            return
        self.meeting_draft.append((meeting.day, meeting.start, meeting.end))
        self.draft_list.controls = [
            ft.Container(
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                bgcolor=CANVAS,
                border_radius=ft.BorderRadius.all(10),
                content=ft.Text(
                    f"{day}  ·  {format_time(int(start[:2]) * 60 + int(start[3:]))}–"
                    f"{format_time(int(end[:2]) * 60 + int(end[3:]))}",
                    size=12,
                    color=INK,
                ),
            )
            for day, start, end in self.meeting_draft
        ]
        self.draft_list.update()
        self._show_status("Meeting added to the section draft.")

    def _save_section(self) -> None:
        try:
            subject = self.engine.add_section(
                self.code.value or "",
                self.title.value or "",
                self.units.value or "",
                self.section.value or "",
                self.slots.value or "",
                list(self.meeting_draft),
            )
        except SchedulingError as exc:
            self._show_status(str(exc), error=True)
            return
        added_section = subject.sections[-1]
        self.meeting_draft.clear()
        self.draft_list.controls = []
        self.section.value = ""
        self.slots.value = ""
        self._refresh_subjects()
        self._refresh_dashboard()
        self._show_status(f"Saved {subject.code}, section {added_section.identifier}.")
        log.info("Added section %s to %s", added_section.identifier, subject.code)

    def _refresh_subjects(self) -> None:
        self.subject_list.controls = []
        if not self.engine.subjects:
            self.subject_list.controls.append(
                ft.Text("No courses yet. Add a section above to get started.", color=MUTED, size=13)
            )
        for subject in self.engine.subjects.values():
            section_summary = "  ·  ".join(
                f"{section.identifier} ({section.slots_left} open)"
                for section in subject.sections
            )
            self.subject_list.controls.append(
                ft.Container(
                    padding=14,
                    bgcolor=CANVAS,
                    border_radius=ft.BorderRadius.all(14),
                    content=ft.Column(
                        spacing=6,
                        controls=[
                            ft.Row(spacing=12, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                                ft.Container(
                                    width=40, height=40, alignment=ft.Alignment.CENTER,
                                    bgcolor=WHITE, border_radius=ft.BorderRadius.all(12),
                                    content=ft.Icon(ft.Icons.MENU_BOOK, size=20, color=ACCENT),
                                ),
                                ft.Column(expand=True, spacing=3, controls=[
                                    ft.Text(f"{subject.code}  ·  {subject.units} units", weight=ft.FontWeight.BOLD, color=INK),
                                    ft.Text(subject.title, size=12, color=MUTED),
                                    ft.Text(f"Sections: {section_summary}", size=11, color=MUTED),
                                ]),
                            ]),
                            ft.Checkbox(
                                label="Pinned", value=subject.pinned,
                                on_change=lambda e, code=subject.code: self._toggle_pin(code, bool(e.control.value)),
                            ),
                        ],
                    ),
                )
            )
        self.subject_list.update()

    def _toggle_pin(self, code: str, pinned: bool) -> None:
        try:
            self.engine.set_pinned(code, pinned)
        except SchedulingError as exc:
            self._show_status(str(exc), error=True)
            self._refresh_subjects()
            return
        self._refresh_dashboard()
        self._show_status(f"{code} {'pinned' if pinned else 'unpinned'}.")

    def _add_blocked(self) -> None:
        try:
            meeting = self.engine.add_blocked_period(
                self.block_day.value or "",
                self.block_start.value or "",
                self.block_end.value or "",
                self.block_reason.value or "",
            )
        except SchedulingError as exc:
            self._show_status(str(exc), error=True)
            return
        self._refresh_blocked_periods()
        self._refresh_dashboard()
        self._show_status("Blocked period added to the base BST.")
        log.info("Added blocked time: %s %s–%s", meeting.day, meeting.start, meeting.end)

    def _refresh_blocked_periods(self) -> None:
        self.blocked_list.controls = []
        blocked_nodes = [node for node in self.engine.base_tree.iter_inorder() if node.blocked]
        if not blocked_nodes:
            self.blocked_list.controls.append(
                ft.Text("No blocked periods have been added.", color=MUTED, size=13)
            )
        for node in blocked_nodes:
            self.blocked_list.controls.append(
                ft.Container(
                    padding=14,
                    bgcolor=CANVAS,
                    border_radius=ft.BorderRadius.all(14),
                    content=ft.Row(
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.EVENT_BUSY, color=ACCENT),
                            ft.Column(
                                expand=True,
                                tight=True,
                                spacing=2,
                                controls=[
                                    ft.Text(f"{node.day}  ·  {format_time(node.key % 1440)}–{format_time(node.end_abs % 1440)}", weight=ft.FontWeight.BOLD, color=INK),
                                    ft.Text(node.reason, size=12, color=MUTED),
                                ],
                            ),
                        ],
                    ),
                )
            )
        self.blocked_list.update()

    def _generate(self) -> None:
        result = self.engine.generate()
        self.results.controls = []
        self.stats.value = (
            f"Search processed {result.states_processed:,} states and evaluated "
            f"{result.complete_candidates:,} complete candidates.  ·  "
            f"Pruned: {result.full_section_rejections:,} full, "
            f"{result.conflict_rejections:,} conflicts, {result.unit_cap_rejections:,} over cap."
        )
        if result.conflict_details:
            self.results.controls.append(
                self._card(
                    ft.Column(
                        spacing=7,
                        controls=[
                            ft.Text("Conflicting choices excluded", weight=ft.FontWeight.BOLD, color=INK),
                            *[ft.Text(detail, size=12, color=MUTED) for detail in result.conflict_details],
                        ],
                    ),
                    bgcolor=CANVAS,
                )
            )
        if result.error:
            self.results.controls.append(self._empty_state(ft.Icons.WARNING, "No schedule could be generated", result.error))
            self._show_status("Search complete — review the constraint message in recommendations.", error=True)
            self.stats.update()
            self.results.update()
            return
        if not result.recommendations:
            self.results.controls.append(self._empty_state(ft.Icons.CALENDAR_MONTH, "No recommendations found", "Review your section availability and constraints."))
        for index, recommendation in enumerate(result.recommendations, start=1):
            self.results.controls.append(self._recommendation_control(index, recommendation))
        self.stats.update()
        self.results.update()
        self._show_status(f"Generated {len(result.recommendations)} ranked recommendation(s).")

    def _metric_chip(self, title: str, value: str, icon) -> ft.Container:
        return ft.Container(
            col={"xs": 6, "sm": 4},
            padding=12,
            bgcolor=CANVAS,
            border_radius=ft.BorderRadius.all(12),
            content=ft.Row(
                spacing=9,
                controls=[
                    ft.Icon(icon, color=ACCENT, size=18),
                    ft.Column(
                        expand=True,
                        tight=True,
                        spacing=1,
                        controls=[ft.Text(value, weight=ft.FontWeight.BOLD, color=INK), ft.Text(title, size=10, color=MUTED)],
                    ),
                ],
            ),
        )

    def _recommendation_control(self, number: int, recommendation) -> ft.Control:
        selected_codes = {code for code, _section in recommendation.state.selected_sections}
        dropped = [code for code in self.engine.subjects if code not in selected_codes]
        card_controls: list[ft.Control] = [
            ft.Row(
                spacing=10,
                controls=[
                    ft.Container(
                        padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                        bgcolor=ACCENT,
                        border_radius=ft.BorderRadius.all(20),
                        content=ft.Text(f"OPTION {number}", size=11, weight=ft.FontWeight.BOLD, color=WHITE),
                    ),
                    ft.Text("Recommended plan", size=17, weight=ft.FontWeight.BOLD, color=INK, expand=True),
                ],
            ),
            ft.ResponsiveRow(
                spacing=10,
                run_spacing=8,
                controls=[
                    self._metric_chip("TOTAL UNITS", f"{recommendation.state.units} / {self.engine.max_units}", ft.Icons.BAR_CHART),
                    self._metric_chip("CAMPUS DAYS", str(recommendation.campus_days), ft.Icons.CALENDAR_TODAY),
                    self._metric_chip("IDLE GAP", f"{recommendation.idle_gap_minutes} min", ft.Icons.SCHEDULE),
                ],
            ),
        ]
        grouped: dict[str, list] = {}
        for node in recommendation.state.tree.iter_inorder():
            if not node.blocked:
                grouped.setdefault(node.day, []).append(node)
        for day in DAYS:
            if day not in grouped:
                continue
            day_rows = [
                ft.Container(
                    padding=ft.Padding.symmetric(horizontal=13, vertical=11),
                    bgcolor=CANVAS,
                    border_radius=ft.BorderRadius.all(12),
                    content=ft.Row(
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(
                                width=4,
                                height=34,
                                bgcolor=ACCENT,
                                border_radius=ft.BorderRadius.all(4),
                            ),
                            ft.Column(
                                expand=True,
                                tight=True,
                                spacing=3,
                                controls=[
                                    ft.Text(
                                        f"{format_time(int(node.start[:2]) * 60 + int(node.start[3:]))} – "
                                        f"{format_time(int(node.end[:2]) * 60 + int(node.end[3:]))}",
                                        size=12,
                                        weight=ft.FontWeight.BOLD,
                                        color=ACCENT,
                                    ),
                                    ft.Text(f"{node.subject_code}  ·  {self.engine.subjects[node.subject_code].title}", weight=ft.FontWeight.W_600, color=INK),
                                    ft.Text(f"Section {node.section}  ·  {self.engine.subjects[node.subject_code].units} unit(s)", size=11, color=MUTED),
                                ],
                            ),
                        ],
                    ),
                )
                for node in grouped[day]
            ]
            card_controls.append(
                ft.Column(
                    spacing=8,
                    controls=[ft.Text(day.upper(), size=12, weight=ft.FontWeight.BOLD, color=MUTED), *day_rows],
                )
            )
        card_controls.append(
            ft.Container(
                padding=ft.Padding.only(top=10),
                content=ft.Text(
                    "Dropped: " + (", ".join(dropped) if dropped else "None"),
                    size=12,
                    color=MUTED,
                ),
            )
        )
        return self._card(ft.Column(spacing=15, controls=card_controls), padding=18)
