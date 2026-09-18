"""Overview page: what the two components are and when to reach for each."""

from __future__ import annotations

import reflex as rx
from reflex_ohif_viewer import ALL_TOOLS, OHIF_MODES, WINDOW_PRESETS

from ..layout import code_block, page, panel

COMPARISON = [
    (
        "What it is",
        "A self-hosted OHIF v3 build in an iframe",
        "A Cornerstone3D viewport inside your component tree",
    ),
    (
        "You get",
        "The whole OHIF product: study list, hanging protocols, "
        "measurement tracking, segmentation, TMTV, microscopy",
        "One viewport, and complete control of the UI around it",
    ),
    (
        "Reflex state",
        "One-way only. Props build the URL; OHIF exposes no cross-frame API",
        "Two-way. Props drive it; slice, window/level and annotations come back as Reflex events",
    ),
    (
        "Deployment",
        "A separate OHIF build to host (Docker image, static assets)",
        "npm packages installed into the Reflex frontend",
    ),
    (
        "Use it when",
        "You want a full diagnostic viewer and do not need Python in the loop",
        "The viewer is part of your app and Python needs to read and drive it",
    ),
]


def comparison_row(label: str, ohif: str, native: str) -> rx.Component:
    """Render one comparison row.

    Args:
        label: The aspect being compared.
        ohif: The OHIF iframe answer.
        native: The native viewport answer.

    Returns:
        The table row.

    """
    return rx.table.row(
        rx.table.row_header_cell(label, style={"white_space": "nowrap"}),
        rx.table.cell(ohif),
        rx.table.cell(native),
    )


def finding(title: str, body: str) -> rx.Component:
    """A short research-finding card.

    Args:
        title: The headline.
        body: The explanation.

    Returns:
        The card component.

    """
    return panel(
        rx.text(title, weight="bold", size="2"),
        rx.text(body, size="2", color=rx.color("gray", 11)),
        flex="1 1 300px",
    )


def index() -> rx.Component:
    """Build the overview page.

    Returns:
        The page component.

    """
    return page(
        "Two ways to view DICOM in Reflex",
        "OHIF Viewer v3 embedded as an iframe, and the Cornerstone3D engine it "
        "is built on wrapped as a native Reflex component.",
        panel(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(""),
                        rx.table.column_header_cell("ohif_viewer()"),
                        rx.table.column_header_cell("dicom_viewer()"),
                    )
                ),
                rx.table.body(*[comparison_row(*row) for row in COMPARISON]),
                variant="surface",
                size="1",
            ),
        ),
        rx.heading("What the research turned up", size="4"),
        rx.flex(
            finding(
                "OHIF publishes no React component",
                "The @ohif/app npm package is a prebuilt static site. Its "
                "package.json points main at dist/index.umd.js, a file the "
                "tarball does not contain. There is no web component either. "
                "An iframe is the only supported embed.",
            ),
            finding(
                "OHIF has no postMessage API",
                "Its own source never posts to, or listens from, a parent "
                "frame. The docs mention postMessage only as something you may "
                "build yourself. So the iframe component is one-way by design.",
            ),
            finding(
                "Cornerstone3D is the way in",
                "OHIF renders with Cornerstone3D, which is published as real "
                "npm libraries. Wrapping it gives a viewport that talks to "
                "Reflex state in both directions.",
            ),
            finding(
                "Bundling is the hard part",
                "Cornerstone decodes frames in web workers with four WASM "
                "codecs and pulls in a few CommonJS packages. CornerstonePlugin "
                "configures Vite for all of it so you do not have to.",
            ),
            wrap="wrap",
            spacing="3",
            width="100%",
        ),
        rx.heading("Quick start", size="4"),
        rx.flex(
            panel(
                rx.text("Native Cornerstone3D viewport", weight="bold", size="2"),
                code_block(
                    """import reflex as rx
from reflex_ohif_viewer import PUBLIC_DICOMWEB_ROOT, dicom_viewer


class State(rx.State):
    measurements: list[dict] = []


def page() -> rx.Component:
    return dicom_viewer(
        wado_rs_root=PUBLIC_DICOMWEB_ROOT,
        study_instance_uid="1.3.6.1.4.1.14519.5.2.1.7009.2403"
                           ".334240657131972136850343327463",
        series_instance_uid="1.3.6.1.4.1.14519.5.2.1.7009.2403"
                            ".226151125820845824875394858561",
        viewport_id="main",
        active_tool="Length",
        window_width=400,
        window_center=40,
        on_measurements_change=State.set_measurements,
        height="70vh",
    )""",
                    "python",
                ),
                flex="1 1 460px",
            ),
            panel(
                rx.text("Embedded OHIF Viewer", weight="bold", size="2"),
                code_block(
                    """import reflex as rx
from reflex_ohif_viewer import ohif_viewer

# docker run -d -p 3001:80 ohif/app:v3.13.8


def page() -> rx.Component:
    return ohif_viewer(
        base_url="http://localhost:3001",
        study_instance_uids=[
            "1.3.6.1.4.1.14519.5.2.1.7009.2403"
            ".871108593056125491804754960339"
        ],
        hanging_protocol_id="mpr",
        height="80vh",
    )""",
                    "python",
                ),
                flex="1 1 460px",
            ),
            wrap="wrap",
            spacing="3",
            width="100%",
        ),
        rx.heading("What ships in the package", size="4"),
        rx.flex(
            panel(
                rx.text(f"{len(ALL_TOOLS)} Cornerstone tools", weight="bold", size="2"),
                rx.text(", ".join(ALL_TOOLS), size="1", color=rx.color("gray", 11)),
                flex="1 1 320px",
            ),
            panel(
                rx.text(f"{len(WINDOW_PRESETS)} window presets", weight="bold", size="2"),
                rx.text(", ".join(WINDOW_PRESETS), size="1", color=rx.color("gray", 11)),
                flex="1 1 240px",
            ),
            panel(
                rx.text(f"{len(OHIF_MODES)} OHIF modes", weight="bold", size="2"),
                rx.text(", ".join(OHIF_MODES), size="1", color=rx.color("gray", 11)),
                flex="1 1 240px",
            ),
            panel(
                rx.text("A Python DICOMweb client", weight="bold", size="2"),
                rx.text(
                    "QIDO-RS study, series and instance search plus WADO-RS "
                    "metadata, so the study browser is ordinary Reflex state.",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                flex="1 1 320px",
            ),
            wrap="wrap",
            spacing="3",
            width="100%",
        ),
    )
