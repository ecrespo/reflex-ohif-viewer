"""Generate the OHIF runtime configuration and the command that serves it."""

from __future__ import annotations

import reflex as rx
from reflex_ohif_viewer import (
    PUBLIC_DICOMWEB_ROOT,
    VERSIONS,
    DicomWebDataSource,
    OhifAppConfig,
    docker_run_command,
)

from ..layout import code_block, page, panel


class DeployState(rx.State):
    """Form state for the OHIF configuration generator."""

    qido_root: str = PUBLIC_DICOMWEB_ROOT
    wado_root: str = PUBLIC_DICOMWEB_ROOT
    source_name: str = "ohif"
    friendly_name: str = "My PACS"
    static_wado: bool = True
    supports_fuzzy_matching: bool = False
    qido_supports_include_field: bool = False
    show_study_list: bool = True
    router_basename: str = "/"
    port: int = 3001
    max_workers: int = 3
    basic_auth: str = ""
    allow_config_url: bool = False

    @rx.event
    def set_qido_root(self, value: str):
        """Change the QIDO-RS root.

        Args:
            value: The new value.

        """
        self.qido_root = value

    @rx.event
    def set_wado_root(self, value: str):
        """Change the WADO-RS root.

        Args:
            value: The new value.

        """
        self.wado_root = value

    @rx.event
    def set_source_name(self, value: str):
        """Change the data source name.

        Args:
            value: The new value.

        """
        self.source_name = value

    @rx.event
    def set_friendly_name(self, value: str):
        """Change the label shown in OHIF's data source picker.

        Args:
            value: The new value.

        """
        self.friendly_name = value

    @rx.event
    def set_router_basename(self, value: str):
        """Change the route prefix the build is served from.

        Args:
            value: The new value.

        """
        self.router_basename = value

    @rx.event
    def set_basic_auth(self, value: str):
        """Set the basic-auth credentials sent to the PACS.

        Args:
            value: The new value.

        """
        self.basic_auth = value

    @rx.event
    def set_static_wado(self, value: bool):
        """Toggle static DICOMweb mode.

        Args:
            value: The new value.

        """
        self.static_wado = value

    @rx.event
    def set_supports_fuzzy_matching(self, value: bool):
        """Toggle fuzzy patient name matching.

        Args:
            value: The new value.

        """
        self.supports_fuzzy_matching = value

    @rx.event
    def set_qido_supports_include_field(self, value: bool):
        """Toggle QIDO includefield support.

        Args:
            value: The new value.

        """
        self.qido_supports_include_field = value

    @rx.event
    def set_show_study_list(self, value: bool):
        """Toggle OHIF's study list route.

        Args:
            value: The new value.

        """
        self.show_study_list = value

    @rx.event
    def set_allow_config_url(self, value: bool):
        """Toggle the ?configUrl= parameter.

        Args:
            value: The new value.

        """
        self.allow_config_url = value

    @rx.event
    def set_port(self, value: str):
        """Change the host port the container publishes on.

        Args:
            value: The port, as typed.

        """
        self.port = int(value) if value.isdigit() else self.port

    @rx.event
    def set_max_workers(self, value: str):
        """Change the frame-decode worker count.

        Args:
            value: The worker count, as typed.

        """
        self.max_workers = int(value) if value.isdigit() else self.max_workers

    def _config(self) -> OhifAppConfig:
        """Build the configuration object from the form.

        Returns:
            The assembled configuration.

        """
        source = DicomWebDataSource(
            source_name=self.source_name or "dicomweb",
            friendly_name=self.friendly_name or "DICOMweb server",
            name=self.source_name or "dicomweb",
            qido_root=self.qido_root,
            wado_root=self.wado_root,
            static_wado=self.static_wado,
            qido_supports_include_field=self.qido_supports_include_field,
            supports_fuzzy_matching=self.supports_fuzzy_matching,
            supports_wildcard=not self.static_wado,
            single_part="bulkdata,video" if self.static_wado else False,
            bulk_data_uri={"enabled": True},
            request_options={"auth": self.basic_auth} if self.basic_auth else None,
        )
        return OhifAppConfig(
            data_sources=[source],
            default_data_source_name=source.source_name,
            router_basename=self.router_basename or "/",
            show_study_list=self.show_study_list,
            max_number_of_web_workers=self.max_workers,
            dangerously_use_dynamic_config=(
                {"enabled": True, "regex": ".*"} if self.allow_config_url else None
            ),
        )

    @rx.var
    def app_config_js(self) -> str:
        """The generated ``app-config.js``.

        Returns:
            JavaScript text assigning ``window.config``.

        """
        try:
            return self._config().to_app_config_js()
        except ValueError as exc:
            return f"// {exc}"

    @rx.var
    def config_json(self) -> str:
        """The generated JSON for the ``?configUrl=`` parameter.

        Returns:
            JSON text.

        """
        try:
            return self._config().to_json()
        except ValueError as exc:
            return f'{{"error": "{exc}"}}'

    @rx.var
    def docker_command(self) -> str:
        """The ``docker run`` command that serves this configuration.

        Returns:
            A shell command.

        """
        try:
            return docker_run_command(
                self._config(),
                port=self.port,
                image=VERSIONS["ohif_docker_image"],
                public_url=self.router_basename or "/",
            )
        except ValueError as exc:
            return f"# {exc}"


def field(label: str, control: rx.Component, hint: str = "") -> rx.Component:
    """One labelled form field.

    Args:
        label: The field label.
        control: The input control.
        hint: Optional help text.

    Returns:
        The field component.

    """
    return rx.vstack(
        rx.text(label, size="1", color=rx.color("gray", 11)),
        control,
        rx.cond(hint != "", rx.text(hint, size="1", color=rx.color("gray", 10))),
        spacing="1",
        align="stretch",
        flex="1 1 250px",
    )


def index() -> rx.Component:
    """Build the deployment page.

    Returns:
        The page component.

    """
    return page(
        "Deploy and configure OHIF",
        "OHIF reads its runtime configuration from a global window.config set by "
        "app-config.js. The official Docker image writes the APP_CONFIG "
        "environment variable over that file at start, so the configuration "
        "below applies without rebuilding the bundle.",
        panel(
            rx.flex(
                field(
                    "QIDO-RS root",
                    rx.input(
                        value=DeployState.qido_root,
                        on_change=DeployState.set_qido_root,
                        size="1",
                    ),
                ),
                field(
                    "WADO-RS root",
                    rx.input(
                        value=DeployState.wado_root,
                        on_change=DeployState.set_wado_root,
                        size="1",
                    ),
                ),
                field(
                    "sourceName",
                    rx.input(
                        value=DeployState.source_name,
                        on_change=DeployState.set_source_name,
                        size="1",
                    ),
                    "The /viewer/<sourceName> path segment.",
                ),
                field(
                    "Friendly name",
                    rx.input(
                        value=DeployState.friendly_name,
                        on_change=DeployState.set_friendly_name,
                        size="1",
                    ),
                ),
                field(
                    "routerBasename",
                    rx.input(
                        value=DeployState.router_basename,
                        on_change=DeployState.set_router_basename,
                        size="1",
                    ),
                    "Leading slash, no trailing slash. Must match PUBLIC_URL.",
                ),
                field(
                    "Host port",
                    rx.input(
                        value=DeployState.port.to_string(),
                        on_change=DeployState.set_port,
                        type="number",
                        size="1",
                    ),
                ),
                field(
                    "Basic auth (user:password)",
                    rx.input(
                        value=DeployState.basic_auth,
                        on_change=DeployState.set_basic_auth,
                        placeholder="(none)",
                        size="1",
                    ),
                    "Sent as Authorization: Basic base64(value).",
                ),
                field(
                    "Web workers",
                    rx.input(
                        value=DeployState.max_workers.to_string(),
                        on_change=DeployState.set_max_workers,
                        type="number",
                        size="1",
                    ),
                    "Above 3 misbehaves on some Windows hosts.",
                ),
                wrap="wrap",
                spacing="3",
                width="100%",
            ),
            rx.flex(
                rx.checkbox(
                    "staticWado (S3/CloudFront static DICOMweb)",
                    checked=DeployState.static_wado,
                    on_change=DeployState.set_static_wado,
                    size="1",
                ),
                rx.checkbox(
                    "supportsFuzzyMatching",
                    checked=DeployState.supports_fuzzy_matching,
                    on_change=DeployState.set_supports_fuzzy_matching,
                    size="1",
                ),
                rx.checkbox(
                    "qidoSupportsIncludeField",
                    checked=DeployState.qido_supports_include_field,
                    on_change=DeployState.set_qido_supports_include_field,
                    size="1",
                ),
                rx.checkbox(
                    "showStudyList",
                    checked=DeployState.show_study_list,
                    on_change=DeployState.set_show_study_list,
                    size="1",
                ),
                rx.checkbox(
                    "Allow ?configUrl=",
                    checked=DeployState.allow_config_url,
                    on_change=DeployState.set_allow_config_url,
                    size="1",
                ),
                wrap="wrap",
                spacing="4",
                width="100%",
            ),
        ),
        rx.flex(
            panel(
                rx.text("docker run", weight="bold", size="2"),
                code_block(DeployState.docker_command, "bash"),
                rx.text(
                    "APP_CONFIG is written over app-config.js by the image's "
                    "entrypoint at start. PUBLIC_URL by contrast is baked in at "
                    "build time and needs a --build-arg on a rebuild.",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                flex="1 1 480px",
            ),
            panel(
                rx.text("app-config.js", weight="bold", size="2"),
                code_block(DeployState.app_config_js, "javascript"),
                flex="1 1 480px",
            ),
            wrap="wrap",
            spacing="3",
            width="100%",
        ),
        panel(
            rx.text("Serving per-session config from Reflex", weight="bold", size="2"),
            rx.text(
                "Turn on ?configUrl= above, serve this JSON from a Reflex API "
                "route, and each session can get its own data source and "
                "credentials without a rebuild. OHIF replaces window.config "
                "wholesale with the fetched document, so it must be pure JSON: "
                "the function-valued fields (httpErrorHandler, whiteLabeling, "
                "requestOptions.auth as a function) cannot be used this way.",
                size="1",
                color=rx.color("gray", 11),
            ),
            code_block(
                """import reflex as rx
from reflex_ohif_viewer import DicomWebDataSource, OhifAppConfig, ohif_viewer


def build_config(token: str) -> OhifAppConfig:
    return OhifAppConfig(
        data_sources=[DicomWebDataSource(
            source_name="pacs",
            qido_root="https://pacs.internal/dicom-web",
            wado_root="https://pacs.internal/dicom-web",
            request_options={"token": token},
        )],
        dangerously_use_dynamic_config={"enabled": True, "regex": ".*"},
    )


app = rx.App()


@app.api.get("/ohif-config.json")
async def ohif_config():
    return build_config(current_session_token()).to_dict()


# ...then point the component at it:
ohif_viewer(
    base_url="http://localhost:3001",
    config_url="http://localhost:3000/ohif-config.json",
    study_instance_uids=[State.study_uid],
)""",
                "python",
            ),
        ),
        panel(
            rx.text("Generated JSON (for ?configUrl=)", weight="bold", size="2"),
            code_block(DeployState.config_json, "json"),
        ),
    )
