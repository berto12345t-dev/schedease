"""SchedEase Flet entry point."""

import logging

import flet as ft

from views.planner import PlannerView

LOG_LEVEL = logging.INFO
logging.basicConfig(format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("app").setLevel(LOG_LEVEL)


async def main(page: ft.Page):
    page.title = "SchedEase Planner"
    page.bgcolor = ft.Colors.BLUE_50
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.add(PlannerView(page).build())


ft.run(main)
