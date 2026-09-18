"""Builders for the OHIF Viewer v3 runtime configuration (``app-config.js``).

An OHIF build reads its configuration from a global ``window.config`` that is
set by ``app-config.js``, loaded before the bundle. Three delivery mechanisms
matter here and all three are supported:

* :meth:`OhifAppConfig.to_app_config_js` — the literal JavaScript text. This is
  what the official ``ohif/app`` Docker image writes over ``app-config.js`` when
  you pass it as the ``APP_CONFIG`` environment variable.
* :meth:`OhifAppConfig.to_json` — a JSON document to serve behind the
  ``?configUrl=`` query parameter. The target build must enable
  ``dangerouslyUseDynamicConfig`` for that parameter to be honoured, and the
  document must be pure JSON, so function-valued fields cannot be used.
* :meth:`OhifAppConfig.to_dict` — the plain mapping, for your own plumbing.

Field names follow ``platform/core/src/types/AppTypes.ts`` and the
``DicomWebConfig`` type in ``extensions/default/src/DicomWebDataSource``.
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any, Literal

from .constants import PUBLIC_DICOMWEB_ROOT

__all__ = [
    "DicomWebDataSource",
    "OhifAppConfig",
    "docker_run_command",
    "public_demo_config",
]

ImageRendering = Literal["wadors", "thumbnail", "thumbnailDirect", "rendered"]


def _prune(mapping: dict[str, Any]) -> dict[str, Any]:
    """Drop ``None`` values so OHIF falls back to its own defaults.

    Args:
        mapping: The mapping to clean.

    Returns:
        A new mapping without ``None`` values.

    """
    return {key: value for key, value in mapping.items() if value is not None}


@dataclasses.dataclass
class DicomWebDataSource:
    """A ``dicomweb`` data source entry for ``window.config.dataSources``.

    Attributes:
        source_name: The name OHIF routes on, i.e. the ``<sourceName>`` in
            ``/viewer/<sourceName>``. Also the value of ``?dataSources=``.
        qido_root: QIDO-RS root for study/series search.
        wado_root: WADO-RS root for metadata and frame retrieval.
        wado_uri_root: WADO-URI root. Defaults to ``wado_root``.
        friendly_name: Label shown in the OHIF data source picker.
        name: Short internal name.
        static_wado: ``True`` for a static DICOMweb bucket (such as the public
            CloudFront demo server), which cannot answer real QIDO queries.
        qido_supports_include_field: Whether the server honours
            ``includefield``. Static DICOMweb servers do not.
        supports_fuzzy_matching: Whether the server supports fuzzy patient
            name matching.
        supports_wildcard: Whether the server supports ``*`` in QIDO filters.
        supports_reject: Whether the server exposes the dcm4chee reject API.
        enable_study_lazy_load: Load series metadata lazily.
        dicom_upload_enabled: Enable STOW-RS upload from the study list.
        image_rendering: How image frames are fetched.
        thumbnail_rendering: How thumbnails are fetched.
        omit_quotation_for_multipart_request: Required by some IIS/.NET servers
            that reject quoted multipart parameters.
        single_part: ``False``, ``True`` or a comma-separated list such as
            ``"bulkdata,video"``.
        bulk_data_uri: The ``bulkDataURI`` sub-configuration.
        request_options: Authentication options. A plain string is sent as
            ``Authorization: Basic base64(value)``; use ``token`` plus the
            ``?token=`` URL parameter, or OIDC, for bearer authentication.
        namespace: The extension namespace providing this data source.
        extra: Any further keys to merge into ``configuration`` verbatim.

    """

    source_name: str = "dicomweb"
    qido_root: str = PUBLIC_DICOMWEB_ROOT
    wado_root: str = PUBLIC_DICOMWEB_ROOT
    wado_uri_root: str | None = None
    friendly_name: str = "DICOMweb server"
    name: str = "dicomweb"
    static_wado: bool = False
    qido_supports_include_field: bool = True
    supports_fuzzy_matching: bool = True
    supports_wildcard: bool = True
    supports_reject: bool = False
    enable_study_lazy_load: bool = True
    dicom_upload_enabled: bool = False
    image_rendering: ImageRendering = "wadors"
    thumbnail_rendering: ImageRendering = "wadors"
    omit_quotation_for_multipart_request: bool = True
    single_part: bool | str = False
    bulk_data_uri: dict[str, Any] | None = None
    request_options: dict[str, Any] | None = None
    namespace: str = "@ohif/extension-default.dataSourcesModule.dicomweb"
    extra: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Render this data source as an OHIF ``dataSources`` entry.

        Returns:
            The mapping OHIF expects inside ``window.config.dataSources``.

        """
        configuration = _prune(
            {
                "friendlyName": self.friendly_name,
                "name": self.name,
                "qidoRoot": self.qido_root,
                "wadoRoot": self.wado_root,
                "wadoUriRoot": self.wado_uri_root or self.wado_root,
                "qidoSupportsIncludeField": self.qido_supports_include_field,
                "supportsFuzzyMatching": self.supports_fuzzy_matching,
                "supportsWildcard": self.supports_wildcard,
                "supportsReject": self.supports_reject,
                "enableStudyLazyLoad": self.enable_study_lazy_load,
                "dicomUploadEnabled": self.dicom_upload_enabled,
                "staticWado": self.static_wado,
                "imageRendering": self.image_rendering,
                "thumbnailRendering": self.thumbnail_rendering,
                "omitQuotationForMultipartRequest": (self.omit_quotation_for_multipart_request),
                "singlepart": self.single_part,
                "bulkDataURI": self.bulk_data_uri,
                "requestOptions": self.request_options,
            }
        )
        configuration.update(self.extra)
        return {
            "namespace": self.namespace,
            "sourceName": self.source_name,
            "configuration": configuration,
        }

    @classmethod
    def public_demo(cls, source_name: str = "ohif") -> DicomWebDataSource:
        """Build the data source for the public OHIF CloudFront demo server.

        Args:
            source_name: The ``sourceName`` to register it under.

        Returns:
            A data source configured for static DICOMweb.

        """
        return cls(
            source_name=source_name,
            friendly_name="OHIF public demo (static DICOMweb)",
            name="ohif-public",
            qido_root=PUBLIC_DICOMWEB_ROOT,
            wado_root=PUBLIC_DICOMWEB_ROOT,
            static_wado=True,
            qido_supports_include_field=False,
            supports_fuzzy_matching=False,
            supports_wildcard=False,
            single_part="bulkdata,video",
            bulk_data_uri={"enabled": True},
        )


@dataclasses.dataclass
class OhifAppConfig:
    """The subset of ``window.config`` that matters for an embedded viewer.

    Attributes:
        data_sources: The configured data sources, in OHIF's order.
        default_data_source_name: ``sourceName`` used when the URL names none.
        router_basename: Route prefix, with a leading and no trailing slash.
            Must match the path the build is served from. The build's
            ``PUBLIC_URL`` (a build-time variable) must agree with it.
        name: A label OHIF echoes back in the debug page.
        show_study_list: Whether the ``/`` study-list route exists.
        max_number_of_web_workers: Decode worker count. Some Windows hosts
            misbehave above 3.
        show_loading_indicator: Show OHIF's own loading indicator.
        show_cpu_fallback_message: Warn when falling back to CPU rendering.
        show_warning_message_for_cross_origin: Warn on cross-origin data.
        strict_z_spacing_for_volume_viewport: Reject irregular z-spacing.
        investigational_use_dialog: ``{"option": "never" | "always" |
            "configure"}``.
        measurement_tracking_mode: ``"standard"``, ``"simplified"`` or
            ``"none"``.
        max_num_requests: Concurrency caps per request type.
        study_prefetcher: The study prefetcher sub-configuration.
        dangerously_use_dynamic_config: Enables the ``?configUrl=`` parameter.
            Supply ``{"enabled": True, "regex": ".*"}`` to allow any URL.
        customization_service: Startup customizations.
        customization_url_prefixes: Allowlist for the ``?customization=``
            parameter.
        extensions: Extra runtime-registered extensions.
        modes: Extra runtime-registered modes.
        extra: Any further top-level keys, merged verbatim and last.

    """

    data_sources: list[DicomWebDataSource] = dataclasses.field(default_factory=list)
    default_data_source_name: str | None = None
    router_basename: str | None = "/"
    name: str = "config/reflex-ohif-viewer.js"
    show_study_list: bool = True
    max_number_of_web_workers: int = 3
    show_loading_indicator: bool = True
    show_cpu_fallback_message: bool = True
    show_warning_message_for_cross_origin: bool = True
    strict_z_spacing_for_volume_viewport: bool = True
    investigational_use_dialog: dict[str, Any] = dataclasses.field(
        default_factory=lambda: {"option": "never"}
    )
    measurement_tracking_mode: str = "standard"
    max_num_requests: dict[str, int] = dataclasses.field(
        default_factory=lambda: {"interaction": 100, "thumbnail": 75, "prefetch": 25}
    )
    study_prefetcher: dict[str, Any] | None = None
    dangerously_use_dynamic_config: dict[str, Any] | None = None
    customization_service: list[Any] | dict[str, Any] | None = None
    customization_url_prefixes: dict[str, str] | None = None
    extensions: list[str] = dataclasses.field(default_factory=list)
    modes: list[str] = dataclasses.field(default_factory=list)
    extra: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Render the configuration as a plain, JSON-safe mapping.

        Returns:
            The ``window.config`` mapping.

        Raises:
            ValueError: If no data sources were configured.

        """
        if not self.data_sources:
            msg = "OhifAppConfig requires at least one data source."
            raise ValueError(msg)

        default_name = self.default_data_source_name or self.data_sources[0].source_name
        config = _prune(
            {
                "name": self.name,
                "routerBasename": self.router_basename,
                "extensions": self.extensions,
                "modes": self.modes,
                "showStudyList": self.show_study_list,
                "maxNumberOfWebWorkers": self.max_number_of_web_workers,
                "showLoadingIndicator": self.show_loading_indicator,
                "showCPUFallbackMessage": self.show_cpu_fallback_message,
                "showWarningMessageForCrossOrigin": (self.show_warning_message_for_cross_origin),
                "strictZSpacingForVolumeViewport": (self.strict_z_spacing_for_volume_viewport),
                "investigationalUseDialog": self.investigational_use_dialog,
                "measurementTrackingMode": self.measurement_tracking_mode,
                "maxNumRequests": self.max_num_requests,
                "studyPrefetcher": self.study_prefetcher,
                "dangerouslyUseDynamicConfig": self.dangerously_use_dynamic_config,
                "customizationService": self.customization_service,
                "customizationUrlPrefixes": self.customization_url_prefixes,
                "defaultDataSourceName": default_name,
                "dataSources": [source.to_dict() for source in self.data_sources],
            }
        )
        config.update(self.extra)
        return config

    def to_json(self, indent: int | None = 2) -> str:
        """Render the configuration as JSON for the ``?configUrl=`` parameter.

        Args:
            indent: JSON indentation, or ``None`` for a compact document.

        Returns:
            The JSON text.

        """
        return json.dumps(self.to_dict(), indent=indent)

    def to_app_config_js(self) -> str:
        """Render the configuration as ``app-config.js`` JavaScript text.

        This is the exact string the ``ohif/app`` Docker image expects in its
        ``APP_CONFIG`` environment variable.

        Returns:
            A JavaScript snippet assigning ``window.config``.

        """
        return f"window.config = {self.to_json()};\n"

    @classmethod
    def public_demo(cls, router_basename: str = "/") -> OhifAppConfig:
        """Build a configuration pointed at the public OHIF demo server.

        Args:
            router_basename: The route prefix the build is served from.

        Returns:
            A ready-to-use configuration.

        """
        return cls(
            data_sources=[DicomWebDataSource.public_demo()],
            default_data_source_name="ohif",
            router_basename=router_basename,
            name="config/reflex-ohif-viewer-demo.js",
        )


def public_demo_config(router_basename: str = "/") -> OhifAppConfig:
    """Shorthand for :meth:`OhifAppConfig.public_demo`.

    Args:
        router_basename: The route prefix the build is served from.

    Returns:
        A ready-to-use configuration.

    """
    return OhifAppConfig.public_demo(router_basename=router_basename)


def docker_run_command(
    config: OhifAppConfig,
    port: int = 3001,
    image: str = "ohif/app:v3.13.8",
    public_url: str = "/",
    container_name: str = "ohif-viewer",
) -> str:
    """Build a ``docker run`` command that serves OHIF with ``config``.

    The official image writes the ``APP_CONFIG`` environment variable over
    ``app-config.js`` on start, so the configuration is applied without
    rebuilding the bundle. ``PUBLIC_URL`` by contrast is baked in at build time
    and can only be changed with a ``--build-arg`` on a rebuild.

    Args:
        config: The configuration to inject.
        port: Host port to publish the viewer on.
        image: The image tag to run. Avoid ``:latest``: it lags the real
            stable release.
        public_url: The ``PUBLIC_URL`` the image was built with.
        container_name: Name for the container.

    Returns:
        A single-line shell command.

    """
    app_config = config.to_app_config_js().replace("'", "'\\''")
    return (
        f"docker run -d --name {container_name} -p {port}:80 "
        f"-e APP_CONFIG='{app_config}' "
        f"-e PUBLIC_URL='{public_url}' "
        f"{image}"
    )
