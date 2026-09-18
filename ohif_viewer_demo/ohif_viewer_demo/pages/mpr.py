"""Multi-planar reformat: three volume viewports sharing one volume and tool group."""

from __future__ import annotations

import reflex as rx
from reflex_ohif_viewer import WINDOW_PRESETS, dicom_viewer, reset_camera

from ..layout import code_block, page, panel
from ..state import ViewerState

#: One tool group for all three viewports is what makes Crosshairs link them;
#: one volume id is what makes the pixel data load once instead of three times.
TOOL_GROUP = "mpr-tools"
VOLUME = "cornerstoneStreamingImageVolume:mpr-demo"

PLANES = (
    ("axial", "Axial", "mpr-axial"),
    ("sagittal", "Sagittal", "mpr-sagittal"),
    ("coronal", "Coronal", "mpr-coronal"),
)

MPR_TOOLS = [
    "WindowLevel",
    "Pan",
    "Zoom",
    "StackScroll",
    "Crosshairs",
    "Length",
    "EllipticalROI",
    "RectangleROI",
    "Probe",
    "Angle",
    "Eraser",
]


def plane(orientation: str, label: str, viewport_id: str) -> rx.Component:
    """One reformatted plane.

    Args:
        orientation: ``axial``, ``sagittal`` or ``coronal``.
        label: The heading shown above the viewport.
        viewport_id: A unique viewport id.

    Returns:
        The viewport card.

    """
    return rx.vstack(
        rx.hstack(
            rx.text(label, size="1", weight="medium"),
            rx.spacer(),
            rx.icon_button(
                rx.icon("maximize", size=13),
                on_click=reset_camera(viewport_id),
                variant="ghost",
                size="1",
            ),
            width="100%",
            align="center",
        ),
        rx.box(
            rx.cond(
                ViewerState.series_uid != "",
                dicom_viewer(
                    wado_rs_root=ViewerState.dicomweb_root,
                    study_instance_uid=ViewerState.study_uid,
                    series_instance_uid=ViewerState.series_uid,
                    viewport_id=viewport_id,
                    rendering_engine_id="mpr-engine",
                    tool_group_id=TOOL_GROUP,
                    volume_id=VOLUME,
                    mode="volume",
                    orientation=orientation,
                    tools=MPR_TOOLS,
                    active_tool=ViewerState.active_tool,
                    window_width=ViewerState.window_width,
                    window_center=ViewerState.window_center,
                    show_overlay=False,
                    width="100%",
                    height="100%",
                ),
                rx.center(rx.spinner(), height="100%"),
            ),
            width="100%",
            height="38vh",
            min_height="260px",
            background="black",
            border_radius="8px",
            overflow="hidden",
            border=f"1px solid {rx.color('gray', 5)}",
        ),
        flex="1 1 320px",
        spacing="1",
        align="stretch",
    )


def index() -> rx.Component:
    """Build the MPR page.

    Returns:
        The page component.

    """
    return page(
        "Multi-planar reformat",
        "Three orthographic viewports over one volume. They share a tool group, "
        "so Crosshairs links them, and a volume id, so the series is decoded "
        "once rather than three times.",
        panel(
            rx.hstack(
                rx.text("Study", size="1", color=rx.color("gray", 11)),
                rx.select(
                    ViewerState.study_options,
                    value=ViewerState.selected_study_label,
                    on_change=ViewerState.select_study,
                    size="1",
                    width="260px",
                ),
                rx.text("Series", size="1", color=rx.color("gray", 11)),
                rx.select(
                    ViewerState.series_labels,
                    value=ViewerState.selected_series_label,
                    on_change=ViewerState.select_series,
                    placeholder="No series",
                    size="1",
                    width="260px",
                ),
                rx.text("Preset", size="1", color=rx.color("gray", 11)),
                rx.select(
                    list(WINDOW_PRESETS),
                    value=ViewerState.window_preset,
                    on_change=ViewerState.apply_window_preset,
                    size="1",
                    width="170px",
                ),
                rx.text("Tool", size="1", color=rx.color("gray", 11)),
                rx.select(
                    MPR_TOOLS,
                    value=ViewerState.active_tool,
                    on_change=ViewerState.set_active_tool,
                    size="1",
                    width="150px",
                ),
                spacing="2",
                align="center",
                wrap="wrap",
                width="100%",
            ),
            rx.text(
                "Pick Crosshairs and drag the coloured reference lines: the other "
                "two planes follow. A volume needs consistent slice spacing, so a "
                "scout or a single-image series will not reformat.",
                size="1",
                color=rx.color("gray", 11),
            ),
        ),
        rx.flex(*[plane(*item) for item in PLANES], spacing="3", wrap="wrap", width="100%"),
        panel(
            rx.text("How the linking works", weight="bold", size="2"),
            code_block(
                """TOOL_GROUP = "mpr-tools"
VOLUME = "cornerstoneStreamingImageVolume:mpr-demo"

for orientation, viewport_id in (
    ("axial", "mpr-axial"),
    ("sagittal", "mpr-sagittal"),
    ("coronal", "mpr-coronal"),
):
    dicom_viewer(
        wado_rs_root=State.root,
        study_instance_uid=State.study_uid,
        series_instance_uid=State.series_uid,
        viewport_id=viewport_id,     # unique per viewport
        tool_group_id=TOOL_GROUP,    # shared: makes Crosshairs link them
        volume_id=VOLUME,            # shared: decode the volume once
        mode="volume",
        orientation=orientation,
        tools=["WindowLevel", "Pan", "Zoom", "Crosshairs", "Length"],
    )""",
                "python",
            ),
        ),
    )
