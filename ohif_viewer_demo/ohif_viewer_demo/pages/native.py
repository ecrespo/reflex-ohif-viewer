"""The native Cornerstone3D viewport, wired to Reflex state in both directions."""

from __future__ import annotations

import reflex as rx
from reflex_ohif_viewer import (
    ANNOTATION_TOOLS,
    COLORMAPS,
    NAVIGATION_TOOLS,
    WINDOW_PRESETS,
    clear_measurements,
    dicom_viewer,
    jump_to_slice,
    remove_measurement,
    reset_camera,
    reset_properties,
    scroll,
)

from ..layout import page, panel
from ..state import ViewerState

VIEWPORT = "main"

TOOL_ICONS = {
    "WindowLevel": "sun-moon",
    "Pan": "move",
    "Zoom": "zoom-in",
    "StackScroll": "chevrons-up-down",
    "Magnify": "search",
    "Length": "ruler",
    "Bidirectional": "cross",
    "RectangleROI": "square",
    "EllipticalROI": "circle",
    "CircleROI": "circle-dot",
    "Angle": "triangle",
    "CobbAngle": "spline",
    "ArrowAnnotate": "arrow-up-right",
    "Probe": "crosshair",
    "PlanarFreehandROI": "pen-tool",
    "Eraser": "eraser",
}

TOOLBAR = (
    "WindowLevel",
    "Pan",
    "Zoom",
    "StackScroll",
    "Magnify",
    "Length",
    "Bidirectional",
    "RectangleROI",
    "EllipticalROI",
    "CircleROI",
    "Angle",
    "ArrowAnnotate",
    "Probe",
    "PlanarFreehandROI",
    "Eraser",
)


def tool_button(name: str) -> rx.Component:
    """One toolbar button that sets the primary mouse tool.

    Args:
        name: The Cornerstone tool name.

    Returns:
        The button component.

    """
    return rx.tooltip(
        rx.button(
            rx.icon(TOOL_ICONS.get(name, "circle"), size=15),
            variant=rx.cond(ViewerState.active_tool == name, "solid", "soft"),
            color_scheme=rx.cond(ViewerState.active_tool == name, "iris", "gray"),
            on_click=ViewerState.set_active_tool(name),
            size="2",
            padding_x="0.55rem",
        ),
        content=name,
    )


def measurement_row(item) -> rx.Component:
    """Render one measurement table row.

    Args:
        item: A ``Measurement`` from the state.

    Returns:
        The table row.

    """
    return rx.table.row(
        rx.table.cell(rx.badge(item.tool, variant="soft", size="1")),
        rx.table.cell(rx.text(item.value, size="1")),
        rx.table.cell(
            rx.icon_button(
                rx.icon("trash-2", size=13),
                variant="ghost",
                color_scheme="red",
                size="1",
                on_click=remove_measurement(VIEWPORT, item.uid),
            ),
            style={"text_align": "right"},
        ),
    )


def sidebar() -> rx.Component:
    """The left-hand control column.

    Returns:
        The sidebar component.

    """
    return rx.vstack(
        panel(
            rx.text("Data source", weight="bold", size="2"),
            rx.input(
                default_value=ViewerState.dicomweb_root,
                on_blur=ViewerState.set_root,
                placeholder="https://host/dicomweb",
                size="1",
            ),
            rx.text("Study", size="1", color=rx.color("gray", 11)),
            rx.select(
                ViewerState.study_options,
                value=ViewerState.selected_study_label,
                on_change=ViewerState.select_study,
                size="1",
                width="100%",
            ),
            rx.text("Series", size="1", color=rx.color("gray", 11)),
            rx.cond(
                ViewerState.loading,
                rx.hstack(rx.spinner(size="1"), rx.text("Loading…", size="1")),
                rx.select(
                    ViewerState.series_labels,
                    value=ViewerState.selected_series_label,
                    on_change=ViewerState.select_series,
                    placeholder="No series",
                    size="1",
                    width="100%",
                ),
            ),
            rx.cond(
                ViewerState.load_error != "",
                rx.callout(
                    ViewerState.load_error,
                    icon="triangle-alert",
                    color_scheme="red",
                    size="1",
                ),
            ),
        ),
        panel(
            rx.text("Rendering", weight="bold", size="2"),
            rx.segmented_control.root(
                rx.segmented_control.item("Stack", value="stack"),
                rx.segmented_control.item("Volume", value="volume"),
                rx.segmented_control.item("3D", value="volume3d"),
                value=ViewerState.mode,
                on_change=ViewerState.set_mode,
                size="1",
                width="100%",
            ),
            rx.text("Window preset", size="1", color=rx.color("gray", 11)),
            rx.select(
                list(WINDOW_PRESETS),
                value=ViewerState.window_preset,
                on_change=ViewerState.apply_window_preset,
                size="1",
                width="100%",
            ),
            rx.hstack(
                rx.text("W", size="1", color=rx.color("gray", 11)),
                rx.text(ViewerState.window_width, size="1", weight="medium"),
                rx.text("L", size="1", color=rx.color("gray", 11)),
                rx.text(ViewerState.window_center, size="1", weight="medium"),
                spacing="2",
            ),
            rx.text("Colormap", size="1", color=rx.color("gray", 11)),
            rx.select(
                ["(none)", *COLORMAPS],
                value=rx.cond(ViewerState.colormap == "", "(none)", ViewerState.colormap),
                on_change=ViewerState.set_colormap,
                size="1",
                width="100%",
            ),
            rx.hstack(
                rx.checkbox(
                    "Invert",
                    checked=ViewerState.invert,
                    on_change=ViewerState.set_invert,
                    size="1",
                ),
                rx.checkbox(
                    "Cine",
                    checked=ViewerState.cine,
                    on_change=ViewerState.set_cine,
                    size="1",
                ),
                rx.checkbox(
                    "Overlay",
                    checked=ViewerState.show_overlay,
                    on_change=ViewerState.set_show_overlay,
                    size="1",
                ),
                spacing="3",
                wrap="wrap",
            ),
            rx.hstack(
                rx.button(
                    "Reset camera",
                    on_click=reset_camera(VIEWPORT),
                    variant="soft",
                    size="1",
                ),
                rx.button(
                    "Reset W/L",
                    on_click=reset_properties(VIEWPORT),
                    variant="soft",
                    size="1",
                ),
                spacing="2",
            ),
        ),
        panel(
            rx.hstack(
                rx.text("Measurements", weight="bold", size="2"),
                rx.badge(ViewerState.measurement_count, variant="soft"),
                rx.spacer(),
                rx.button(
                    "Clear",
                    on_click=clear_measurements(VIEWPORT),
                    variant="soft",
                    color_scheme="red",
                    size="1",
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                ViewerState.measurement_count > 0,
                rx.box(
                    rx.table.root(
                        rx.table.body(rx.foreach(ViewerState.measurements, measurement_row)),
                        size="1",
                    ),
                    max_height="240px",
                    overflow="auto",
                    width="100%",
                ),
                rx.text(
                    "Pick a measurement tool and drag on the image.",
                    size="1",
                    color=rx.color("gray", 10),
                ),
            ),
        ),
        width="320px",
        min_width="320px",
        spacing="3",
        align="stretch",
    )


def index() -> rx.Component:
    """Build the native viewport page.

    Returns:
        The page component.

    """
    return page(
        "Native Cornerstone3D viewport",
        "Everything on this page is Reflex state. The toolbar, presets and "
        "measurement table on the left are driven from Python; the slice, "
        "window/level and annotations flow back the same way.",
        rx.flex(
            sidebar(),
            rx.vstack(
                rx.hstack(
                    rx.hstack(*[tool_button(name) for name in TOOLBAR], spacing="1", wrap="wrap"),
                    rx.spacer(),
                    rx.cond(
                        ViewerState.ready,
                        rx.badge(ViewerState.viewer_summary, variant="soft", size="1"),
                        rx.badge("loading…", variant="soft", color_scheme="gray", size="1"),
                    ),
                    width="100%",
                    align="center",
                    wrap="wrap",
                    spacing="2",
                ),
                rx.cond(
                    ViewerState.viewer_error != "",
                    rx.callout(
                        ViewerState.viewer_error,
                        icon="triangle-alert",
                        color_scheme="red",
                        size="1",
                        width="100%",
                    ),
                ),
                rx.box(
                    rx.cond(
                        ViewerState.series_uid != "",
                        dicom_viewer(
                            wado_rs_root=ViewerState.dicomweb_root,
                            study_instance_uid=ViewerState.study_uid,
                            series_instance_uid=ViewerState.series_uid,
                            viewport_id=VIEWPORT,
                            rendering_engine_id="demo-engine",
                            mode=ViewerState.mode,
                            active_tool=ViewerState.active_tool,
                            tools=list(NAVIGATION_TOOLS + ANNOTATION_TOOLS),
                            window_width=ViewerState.window_width,
                            window_center=ViewerState.window_center,
                            colormap=ViewerState.colormap,
                            invert=ViewerState.invert,
                            cine=ViewerState.cine,
                            show_overlay=ViewerState.show_overlay,
                            on_viewer_ready=ViewerState.on_viewer_ready,
                            on_slice_change=ViewerState.on_slice_change,
                            on_voi_change=ViewerState.on_voi_change,
                            on_measurements_change=ViewerState.on_measurements_change,
                            on_error=ViewerState.on_viewer_error,
                            width="100%",
                            height="100%",
                        ),
                        rx.center(
                            rx.text("Select a series", color=rx.color("gray", 10)),
                            height="100%",
                        ),
                    ),
                    width="100%",
                    height="68vh",
                    min_height="420px",
                    border_radius="10px",
                    overflow="hidden",
                    border=f"1px solid {rx.color('gray', 5)}",
                    background="black",
                ),
                rx.hstack(
                    rx.icon_button(
                        rx.icon("chevron-left", size=15),
                        on_click=scroll(VIEWPORT, -1),
                        variant="soft",
                        size="1",
                    ),
                    rx.icon_button(
                        rx.icon("chevron-right", size=15),
                        on_click=scroll(VIEWPORT, 1),
                        variant="soft",
                        size="1",
                    ),
                    rx.text(ViewerState.slice_caption, size="1", width="120px"),
                    rx.slider(
                        value=[ViewerState.slice_index],
                        min=0,
                        max=rx.cond(ViewerState.slice_total > 0, ViewerState.slice_total - 1, 0),
                        step=1,
                        on_change=lambda value: jump_to_slice(VIEWPORT, value[0]),
                        width="100%",
                        size="1",
                    ),
                    width="100%",
                    align="center",
                    spacing="2",
                ),
                rx.text(
                    "Left drag runs the selected tool · right drag zooms · middle "
                    "drag or Ctrl+drag pans · wheel or Alt+drag scrolls · Escape "
                    "cancels a half-drawn annotation.",
                    size="1",
                    color=rx.color("gray", 10),
                ),
                flex="1",
                min_width="420px",
                spacing="2",
                align="stretch",
            ),
            spacing="4",
            width="100%",
            wrap="wrap",
            align="start",
        ),
    )
