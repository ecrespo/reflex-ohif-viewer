"""``ohif_viewer`` — embed a self-hosted OHIF Viewer v3 build in a Reflex app.

OHIF v3 is a complete React application, not a component library. Checked
against the 3.13.8 source and the published npm tarballs:

* ``@ohif/app`` on npm is a **prebuilt static site**; its ``main`` field points
  at ``dist/index.umd.js``, a file the tarball does not contain. There is no
  importable React component and no web component.
* OHIF application code never calls ``postMessage`` and never reads a message
  from a parent frame. The four mentions of postMessage in its docs describe
  something *you* may build, not a feature it ships.

The supported way to embed it is therefore an **iframe pointed at your own OHIF
build**, configured entirely through URL query parameters and a runtime
``app-config.js``. That is what this component does, and
:func:`build_ohif_url` is the same URL builder available as a plain function so
you can compute and test links server-side.

See :mod:`reflex_ohif_viewer.ohif_config` for generating the matching
``app-config.js`` (including the ``APP_CONFIG`` environment variable the
official Docker image reads).
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

import reflex as rx

from ._assets import ohif_viewer_library
from .constants import OHIF_WORKLIST_KEYS

__all__ = ["OhifViewer", "build_ohif_url", "ohif_viewer"]

# Query keys OHIF reads on the viewer routes, mapped from Python prop names.
# Sourced from platform/app/src/routes/Mode/Mode.tsx and defaultRouteInit.ts.
_VIEWER_PARAMS: dict[str, str] = {
    "initial_series_instance_uid": "initialSeriesInstanceUID",
    "initial_sop_instance_uid": "initialSopInstanceUID",
    "hanging_protocol_id": "hangingProtocolId",
    "stage_id": "stageId",
    "token": "token",
    "customization": "customization",
    "theme": "theme",
    "use_next_viewports": "useNextViewports",
    "viewport_rendering": "viewportRendering",
    "multimonitor": "multimonitor",
    "screen_number": "screenNumber",
}


def build_ohif_url(
    base_url: str,
    *,
    mode: str = "viewer",
    data_source: str = "",
    study_instance_uids: list[str] | str | None = None,
    series_instance_uids: list[str] | str | None = None,
    study_list: bool = False,
    config_url: str = "",
    debug: bool = False,
    extra_params: dict[str, Any] | None = None,
    **options: Any,
) -> str:
    """Build the URL for an OHIF Viewer v3 route.

    Route shape, from ``platform/app/src/routes/buildModeRoutes.tsx``::

        {base}/{modeRouteName}[/{dataSourceName}]?{query}

    The mode segment is a mode's ``routeName``, not its package id. The plain
    "basic viewer" is ``viewer`` (from ``@ohif/mode-longitudinal``); there is no
    ``basic-viewer`` route.

    Args:
        base_url: Where the OHIF build is served, e.g. ``http://localhost:3001``
            or a same-origin path such as ``/ohif``. Must match the build's
            ``routerBasename`` / ``PUBLIC_URL``.
        mode: The mode route segment. Ignored when ``study_list`` is true.
        data_source: The ``sourceName`` path segment. Omit to use the build's
            ``defaultDataSourceName``.
        study_instance_uids: One or more studies to open. Repeating the
            parameter loads a current study plus priors.
        series_instance_uids: Restrict loading to these series. This is a hard
            filter; use ``initial_series_instance_uid`` to merely start there.
        study_list: Open the study list (``/``) instead of a viewer mode, with
            the worklist filter keys taken from ``options``.
        config_url: Value for ``?configUrl=``. Only honoured when the target
            build sets ``dangerouslyUseDynamicConfig``. Read case-sensitively
            by OHIF, so the casing here is deliberate.
        debug: Add ``?debug=true``.
        extra_params: Extra query parameters, merged last. Note that OHIF turns
            unrecognised viewer parameters into series-level QIDO filters.
        **options: Viewer parameters (``hanging_protocol_id``, ``token``,
            ``initial_series_instance_uid``, ``theme``, …) or, with
            ``study_list=True``, worklist filters (``patient_name``, ``mrn``,
            ``accession``, ``modalities``, ``start_date``, ``end_date``,
            ``sort_by``, ``sort_direction``, ``page_number``,
            ``results_per_page``, ``description``).

    Returns:
        The full URL, or an empty string when ``base_url`` is empty.

    Example:
        ```python
        build_ohif_url(
            "http://localhost:3001",
            study_instance_uids=["1.2.3"],
            hanging_protocol_id="mpr",
        )
        # 'http://localhost:3001/viewer?StudyInstanceUIDs=1.2.3&hangingProtocolId=mpr'
        ```

    """
    if not base_url:
        return ""

    def as_list(value: list[str] | str | None) -> list[str]:
        """Normalise a scalar-or-list argument into a list of strings.

        Args:
            value: The raw argument.

        Returns:
            Non-empty, stripped string values.

        """
        if not value:
            return []
        items = [value] if isinstance(value, str) else list(value)
        return [str(item).strip() for item in items if str(item).strip()]

    trimmed = base_url.rstrip("/")
    pairs: list[tuple[str, str]] = []

    if study_list:
        for key in OHIF_WORKLIST_KEYS:
            snake = "".join(f"_{char.lower()}" if char.isupper() else char for char in key)
            value = options.get(snake, options.get(key, ""))
            if value not in ("", None):
                pairs.append((key, str(value)))
        if data_source:
            pairs.append(("dataSources", data_source))
        path = ""
    else:
        for uid in as_list(study_instance_uids):
            pairs.append(("StudyInstanceUIDs", uid))
        series = as_list(series_instance_uids)
        if series:
            pairs.append(("SeriesInstanceUIDs", ",".join(series)))
        for snake, key in _VIEWER_PARAMS.items():
            value = options.get(snake)
            if value in ("", None, False):
                continue
            pairs.append((key, "true" if value is True else str(value)))
        path = f"{mode}/{data_source}" if data_source else mode

    if config_url:
        pairs.append(("configUrl", config_url))
    if debug:
        pairs.append(("debug", "true"))
    for key, value in (extra_params or {}).items():
        if value not in ("", None):
            pairs.append((key, str(value)))

    url = f"{trimmed}/{path}" if path else f"{trimmed}/"
    query = urlencode(pairs)
    return f"{url}?{query}" if query else url


class OhifViewer(rx.Component):
    """An iframe wrapping a self-hosted OHIF Viewer v3 build.

    All props feed the URL builder, so changing a Reflex state var that is bound
    to ``study_instance_uids`` navigates the embedded viewer.

    Hosting notes:

    * Run your own build. The official image works and sets no
      ``X-Frame-Options``: ``docker run -d -p 3001:80 ohif/app:v3.13.8``. Pin
      the tag — the ``:latest`` tag lags the real stable release.
    * Do not iframe ``viewer.ohif.org``: the project's deployment config sets
      ``X-Frame-Options: DENY``.
    * Serving the build under a sub-path needs both a build-time
      ``PUBLIC_URL=/ohif/`` (trailing slash) and a runtime
      ``routerBasename: '/ohif'`` (no trailing slash).
    * Any static host must rewrite unknown paths to ``index.html`` or a direct
      load of ``/viewer?StudyInstanceUIDs=...`` returns 404.

    Example:
        ```python
        ohif_viewer(
            base_url="http://localhost:3001",
            study_instance_uids=[State.study_uid],
            hanging_protocol_id="mpr",
            height="80vh",
            on_viewer_load=State.handle_loaded,
        )
        ```

    """

    tag = "RxOhifViewer"
    is_default = True

    # --- target ----------------------------------------------------------

    # Where the OHIF build is served from.
    base_url: rx.Var[str] = rx.Var.create("")

    # The mode route segment: ``viewer``, ``segmentation``, ``tmtv``, ``microscopy``,
    # ``dynamic-volume``, ``usAnnotation``, ``basic``.
    mode: rx.Var[str] = rx.Var.create("viewer")

    # The ``sourceName`` path segment. Empty uses the build's default.
    data_source: rx.Var[str] = rx.Var.create("")

    # Open the study list instead of a viewer mode.
    study_list: rx.Var[bool] = rx.Var.create(False)

    # --- what to open ----------------------------------------------------

    # Studies to load. Several entries load a current study plus priors.
    study_instance_uids: rx.Var[list[str]] = rx.Var.create([])

    # Hard filter: only these series are retrieved.
    series_instance_uids: rx.Var[list[str]] = rx.Var.create([])

    # Soft: load the whole study but start on this series.
    initial_series_instance_uid: rx.Var[str] = rx.Var.create("")

    # Navigate to this instance on load.
    initial_sop_instance_uid: rx.Var[str] = rx.Var.create("")

    # A registered hanging protocol id, e.g. ``mpr`` or ``@ohif/mnGrid``.
    hanging_protocol_id: rx.Var[str] = rx.Var.create("")

    # A stage within the hanging protocol.
    stage_id: rx.Var[str] = rx.Var.create("")

    # --- auth / configuration --------------------------------------------

    # Bearer token for the data source. OHIF strips it from the URL after reading it, but it is
    # still a credential in a URL — prefer OIDC or a same-origin proxy for anything sensitive.
    token: rx.Var[str] = rx.Var.create("")

    # URL of a JSON config for ``?configUrl=``. Requires the target build to enable
    # ``dangerouslyUseDynamicConfig``.
    config_url: rx.Var[str] = rx.Var.create("")

    # A customization bundle name, subject to the build's ``customizationUrlPrefixes`` allowlist.
    customization: rx.Var[str] = rx.Var.create("")

    # Theme name, preserved across OHIF's own navigation.
    theme: rx.Var[str] = rx.Var.create("")

    # Add ``?debug=true``.
    debug: rx.Var[bool] = rx.Var.create(False)

    # Opt into the Cornerstone "next" generic viewport API.
    use_next_viewports: rx.Var[bool] = rx.Var.create(False)

    # ``cpu``, ``webgl``, ``auto`` or a backend id.
    viewport_rendering: rx.Var[str] = rx.Var.create("")

    # Extra query parameters, merged last.
    extra_params: rx.Var[dict[str, str]] = rx.Var.create({})

    # Study-list filters, used when ``study_list`` is true. Keys are OHIF's own: ``patientName``,
    # ``mrn``, ``description``, ``accession``, ``modalities``, ``startDate``, ``endDate``,
    # ``sortBy``, ``sortDirection``, ``pageNumber``, ``resultsPerPage``.
    worklist_filters: rx.Var[dict[str, str]] = rx.Var.create({})

    # --- frame -----------------------------------------------------------

    # ``title`` attribute of the iframe, for assistive technology.
    title: rx.Var[str] = rx.Var.create("OHIF Viewer")

    # ``allow`` attribute. Keep ``cross-origin-isolated`` if the OHIF build is served with COOP/COEP
    # for SharedArrayBuffer progressive loading.
    allow: rx.Var[str] = rx.Var.create(
        "cross-origin-isolated; fullscreen; clipboard-read; clipboard-write"
    )

    # ``sandbox`` attribute. Empty means no sandbox attribute is emitted. OHIF needs at least
    # ``allow-scripts allow-same-origin`` to run.
    sandbox: rx.Var[str] = rx.Var.create("")

    # ``referrerpolicy`` attribute.
    referrer_policy: rx.Var[str] = rx.Var.create("no-referrer-when-downgrade")

    # --- events ----------------------------------------------------------

    # Fired when the iframe finishes loading. Receives the URL.
    on_viewer_load: rx.EventHandler[lambda url: [url]]

    # Fired when the computed URL changes. Receives the URL.
    on_url_change: rx.EventHandler[lambda url: [url]]

    # Fired for ``postMessage`` messages from the frame, filtered by origin. OHIF sends none by
    # default; this is for deployments that add their own OHIF extension or serve OHIF behind a
    # same-origin shim.
    on_viewer_message: rx.EventHandler[lambda data: [data]]

    @classmethod
    def create(cls, *children, **props) -> rx.Component:
        """Create the component, linking its frontend asset on first use.

        Args:
            *children: Ignored; the iframe has no Reflex children.
            **props: Component props.

        Returns:
            The configured component.

        """
        component = super().create(*children, **props)
        component.library = ohif_viewer_library()
        return component


ohif_viewer = OhifViewer.create
