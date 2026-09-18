"""reflex-ohif-viewer — OHIF Viewer and Cornerstone3D DICOM viewing for Reflex.

Two complementary components:

``ohif_viewer``
    Embeds a self-hosted OHIF Viewer v3 build in an iframe, driven by URL query
    parameters. You get the complete OHIF product — study list, hanging
    protocols, measurement tracking, segmentation, TMTV, microscopy — at the
    cost of a separately deployed build and no cross-frame API.

``dicom_viewer``
    A native Cornerstone3D viewport, the same engine OHIF renders with, living
    inside the Reflex component tree. You get real two-way binding with
    ``rx.State`` — props drive the viewport, and annotations, window/level and
    slice changes come back as Reflex events — at the cost of building your own
    UI around it.

Supporting pieces: :mod:`~reflex_ohif_viewer.ohif_config` builds OHIF's
``app-config.js``, :mod:`~reflex_ohif_viewer.dicomweb` queries a DICOMweb server
from Python, and :class:`~reflex_ohif_viewer.plugin.CornerstonePlugin` keeps the
WASM codecs working through the bundler.
"""

from .constants import (
    ALL_TOOLS,
    ANNOTATION_TOOLS,
    COLORMAPS,
    CORNERSTONE_CODEC_PACKAGES,
    CORNERSTONE_PACKAGES,
    DEFAULT_TOOLS,
    DEMO_ABDOMEN_CT,
    DEMO_CHEST_CT,
    DEMO_PET_CT,
    DEMO_RTSTRUCT,
    DEMO_STUDIES,
    NAVIGATION_TOOLS,
    OHIF_HANGING_PROTOCOLS,
    OHIF_MODES,
    OVERLAY_TOOLS,
    PUBLIC_DICOMWEB_ROOT,
    PUBLIC_DICOMWEB_ROOT_ALT,
    SEGMENTATION_TOOLS,
    VERSIONS,
    VOLUME_RENDERING_PRESETS,
    WINDOW_PRESETS,
    DemoStudy,
)
from .dicom_viewer import (
    DicomViewer,
    clear_measurements,
    dicom_viewer,
    flip,
    jump_to_slice,
    play_cine,
    remove_measurement,
    reset_camera,
    reset_properties,
    rotate,
    scroll,
    set_colormap,
    set_tool,
    set_window,
    set_window_preset,
    set_zoom,
    stop_cine,
    viewer_call,
    window_preset_range,
)
from .dicomweb import (
    DicomWebClient,
    DicomWebError,
    SeriesSummary,
    StudySummary,
)
from .ohif_config import (
    DicomWebDataSource,
    OhifAppConfig,
    docker_run_command,
    public_demo_config,
)
from .ohif_viewer import OhifViewer, build_ohif_url, ohif_viewer
from .plugin import CornerstonePlugin

__version__ = "0.1.0"

__all__ = [
    "ALL_TOOLS",
    "ANNOTATION_TOOLS",
    "COLORMAPS",
    "CORNERSTONE_CODEC_PACKAGES",
    "CORNERSTONE_PACKAGES",
    "DEFAULT_TOOLS",
    "DEMO_ABDOMEN_CT",
    "DEMO_CHEST_CT",
    "DEMO_PET_CT",
    "DEMO_RTSTRUCT",
    "DEMO_STUDIES",
    "NAVIGATION_TOOLS",
    "OHIF_HANGING_PROTOCOLS",
    "OHIF_MODES",
    "OVERLAY_TOOLS",
    "PUBLIC_DICOMWEB_ROOT",
    "PUBLIC_DICOMWEB_ROOT_ALT",
    "SEGMENTATION_TOOLS",
    "VERSIONS",
    "VOLUME_RENDERING_PRESETS",
    "WINDOW_PRESETS",
    "CornerstonePlugin",
    "DemoStudy",
    "DicomViewer",
    "DicomWebClient",
    "DicomWebDataSource",
    "DicomWebError",
    "OhifAppConfig",
    "OhifViewer",
    "SeriesSummary",
    "StudySummary",
    "build_ohif_url",
    "clear_measurements",
    "dicom_viewer",
    "docker_run_command",
    "flip",
    "jump_to_slice",
    "ohif_viewer",
    "play_cine",
    "public_demo_config",
    "remove_measurement",
    "reset_camera",
    "reset_properties",
    "rotate",
    "scroll",
    "set_colormap",
    "set_tool",
    "set_window",
    "set_window_preset",
    "set_zoom",
    "stop_cine",
    "viewer_call",
    "window_preset_range",
]
