"""The OHIF iframe page: build a viewer URL from state and embed the result."""

from __future__ import annotations

import reflex as rx
from reflex_ohif_viewer import (
    DEMO_STUDIES,
    OHIF_HANGING_PROTOCOLS,
    OHIF_MODES,
    build_ohif_url,
    ohif_viewer,
)

from ..layout import code_block, page, panel
from ..state import ViewerState


class OhifState(rx.State):
    """State for the OHIF iframe page.

    Nothing here reaches into the viewer: OHIF exposes no cross-frame API, so
    every control below works by rebuilding the URL the iframe points at.
    """

    base_url: str = ""
    study_slug: str = "pet-ct"
    mode: str = "viewer"
    hanging_protocol: str = ""
    data_source: str = ""
    theme: str = ""
    show_study_list: bool = False
    debug: bool = False
    loaded_url: str = ""

    @rx.var
    def study_uid(self) -> str:
        """The StudyInstanceUID of the selected demo study.

        Returns:
            The study UID.

        """
        study = DEMO_STUDIES.get(self.study_slug)
        return study.study_instance_uid if study else ""

    @rx.var
    def study_uids(self) -> list[str]:
        """The study UID as the list the component expects.

        Returns:
            A single-element list, or an empty one.

        """
        return [self.study_uid] if self.study_uid else []

    @rx.var
    def preview_url(self) -> str:
        """The URL the component will build, computed server-side too.

        The Python builder and the JavaScript one are kept in step deliberately,
        so a URL can be produced, logged and tested without a browser.

        Returns:
            The OHIF URL, or a placeholder message.

        """
        if not self.base_url:
            return "Set a base URL to see the generated link."
        return build_ohif_url(
            self.base_url,
            mode=self.mode,
            data_source=self.data_source,
            study_instance_uids=self.study_uids,
            study_list=self.show_study_list,
            hanging_protocol_id=self.hanging_protocol,
            theme=self.theme,
            debug=self.debug,
        )

    @rx.event
    def set_base_url(self, value: str):
        """Point the iframe at a different OHIF build.

        Args:
            value: The new value.

        """
        self.base_url = value

    @rx.event
    def set_mode(self, value: str):
        """Change the OHIF mode route.

        Args:
            value: The new value.

        """
        self.mode = value

    @rx.event
    def set_study_slug(self, value: str):
        """Change the demo study.

        Args:
            value: The new value.

        """
        self.study_slug = value

    @rx.event
    def set_data_source(self, value: str):
        """Change the OHIF data source path segment.

        Args:
            value: The new value.

        """
        self.data_source = value

    @rx.event
    def set_show_study_list(self, value: bool):
        """Toggle between the study list and a viewer mode.

        Args:
            value: The new value.

        """
        self.show_study_list = value

    @rx.event
    def set_debug(self, value: bool):
        """Toggle OHIF's debug query parameter.

        Args:
            value: The new value.

        """
        self.debug = value

    @rx.event
    def set_hanging_protocol(self, value: str):
        """Choose a hanging protocol, or fall back to the mode's own.

        Args:
            value: A protocol id, or ``"(mode default)"``.

        """
        self.hanging_protocol = "" if value == "(mode default)" else value

    @rx.event
    def set_loaded(self, url: str):
        """Record the URL the iframe finished loading.

        Args:
            url: The loaded URL.

        """
        self.loaded_url = url


def index() -> rx.Component:
    """Build the OHIF iframe page.

    Returns:
        The page component.

    """
    return page(
        "Embedded OHIF Viewer",
        "OHIF v3 ships no importable React component and no postMessage API, so "
        "the supported embed is an iframe driven by URL query parameters. This "
        "page builds that URL from Reflex state.",
        rx.callout(
            "You need your own OHIF build. Start one with "
            "`docker run -d -p 3001:80 ohif/app:v3.13.8`, then put "
            "http://localhost:3001 in the field below. Pin the tag: the :latest "
            "tag lags the real stable release. Do not point this at "
            "viewer.ohif.org — that deployment sets X-Frame-Options: DENY.",
            icon="info",
            size="1",
            width="100%",
        ),
        panel(
            rx.flex(
                rx.vstack(
                    rx.text("OHIF base URL", size="1", color=rx.color("gray", 11)),
                    rx.input(
                        value=OhifState.base_url,
                        on_change=OhifState.set_base_url,
                        placeholder="http://localhost:3001",
                        size="1",
                        width="100%",
                    ),
                    flex="1 1 260px",
                    spacing="1",
                    align="stretch",
                ),
                rx.vstack(
                    rx.text("Mode (route)", size="1", color=rx.color("gray", 11)),
                    rx.select(
                        list(OHIF_MODES),
                        value=OhifState.mode,
                        on_change=OhifState.set_mode,
                        size="1",
                        width="100%",
                    ),
                    flex="1 1 170px",
                    spacing="1",
                    align="stretch",
                ),
                rx.vstack(
                    rx.text("Hanging protocol", size="1", color=rx.color("gray", 11)),
                    rx.select(
                        ["(mode default)", *OHIF_HANGING_PROTOCOLS],
                        value=rx.cond(
                            OhifState.hanging_protocol == "",
                            "(mode default)",
                            OhifState.hanging_protocol,
                        ),
                        on_change=OhifState.set_hanging_protocol,
                        size="1",
                        width="100%",
                    ),
                    flex="1 1 200px",
                    spacing="1",
                    align="stretch",
                ),
                rx.vstack(
                    rx.text("Study", size="1", color=rx.color("gray", 11)),
                    rx.select(
                        list(DEMO_STUDIES),
                        value=OhifState.study_slug,
                        on_change=OhifState.set_study_slug,
                        size="1",
                        width="100%",
                    ),
                    flex="1 1 150px",
                    spacing="1",
                    align="stretch",
                ),
                rx.vstack(
                    rx.text("Data source", size="1", color=rx.color("gray", 11)),
                    rx.input(
                        value=OhifState.data_source,
                        on_change=OhifState.set_data_source,
                        placeholder="(build default)",
                        size="1",
                        width="100%",
                    ),
                    flex="1 1 150px",
                    spacing="1",
                    align="stretch",
                ),
                wrap="wrap",
                spacing="3",
                width="100%",
            ),
            rx.hstack(
                rx.checkbox(
                    "Open the study list instead",
                    checked=OhifState.show_study_list,
                    on_change=OhifState.set_show_study_list,
                    size="1",
                ),
                rx.checkbox(
                    "debug=true",
                    checked=OhifState.debug,
                    on_change=OhifState.set_debug,
                    size="1",
                ),
                spacing="4",
            ),
            rx.text("Generated URL", size="1", color=rx.color("gray", 11)),
            code_block(OhifState.preview_url, "uri"),
        ),
        rx.box(
            ohif_viewer(
                base_url=OhifState.base_url,
                mode=OhifState.mode,
                data_source=OhifState.data_source,
                study_instance_uids=OhifState.study_uids,
                study_list=OhifState.show_study_list,
                hanging_protocol_id=OhifState.hanging_protocol,
                theme=OhifState.theme,
                debug=OhifState.debug,
                on_viewer_load=OhifState.set_loaded,
                on_url_change=ViewerState.on_ohif_url_change,
                width="100%",
                height="100%",
            ),
            width="100%",
            height="72vh",
            min_height="460px",
            border=f"1px solid {rx.color('gray', 5)}",
            border_radius="10px",
            overflow="hidden",
            background="black",
        ),
        rx.flex(
            panel(
                rx.text("Route shape", weight="bold", size="2"),
                code_block(
                    """{base}/{modeRouteName}[/{dataSourceName}]?{query}

/viewer?StudyInstanceUIDs=<uid>
/viewer/ohif?StudyInstanceUIDs=<uid>&hangingProtocolId=mpr
/viewer?StudyInstanceUIDs=<current>&StudyInstanceUIDs=<prior>
/segmentation?StudyInstanceUIDs=<uid>
/tmtv?StudyInstanceUIDs=<uid>
/?patientName=Smith&modalities=CT,MR&sortDirection=desc""",
                    "http",
                ),
                rx.text(
                    "The mode segment is a mode's routeName, not its package id. "
                    "The plain basic viewer is /viewer, from "
                    "@ohif/mode-longitudinal; there is no /basic-viewer route.",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                flex="1 1 380px",
            ),
            panel(
                rx.text("What the iframe cannot do", weight="bold", size="2"),
                rx.text(
                    "OHIF's source never posts a message to its parent and never "
                    "listens for one. Its docs mention postMessage only as "
                    "something you may implement yourself. So there is no way to "
                    "read the active measurement, the current slice, or the "
                    "window level out of the iframe, and no way to command it "
                    "other than by changing the URL.",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                rx.text(
                    "If you need that, either serve OHIF same-origin and reach "
                    "contentWindow yourself (private API, unstable across minor "
                    "versions), ship your own OHIF extension that speaks "
                    "postMessage — the on_viewer_message event is already wired "
                    "for it — or use the native viewport instead.",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                flex="1 1 380px",
            ),
            wrap="wrap",
            spacing="3",
            width="100%",
        ),
    )
