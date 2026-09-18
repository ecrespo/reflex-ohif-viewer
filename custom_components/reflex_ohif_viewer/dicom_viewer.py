"""``dicom_viewer`` — a native Cornerstone3D viewport for Reflex.

Cornerstone3D is the rendering and tooling engine the OHIF Viewer is built on.
Wrapping it directly gives a viewport that lives *inside* the Reflex component
tree: props are driven from ``rx.State``, and annotations, window/level changes
and slice changes come back as Reflex events. That is something an OHIF iframe
cannot offer, because OHIF exposes no cross-frame API.

The component subclasses :class:`~reflex.components.component.NoSSRComponent`
and additionally loads every Cornerstone module through a dynamic ``import()``
inside an effect, so nothing touches ``window`` during the production build's
prerender pass.
"""

from __future__ import annotations

from typing import Any, Literal

import reflex as rx
from reflex.components.component import NoSSRComponent

from ._assets import dicom_viewer_library
from .constants import (
    ALL_TOOLS,
    CORNERSTONE_PACKAGES,
    DEFAULT_TOOLS,
    WINDOW_PRESETS,
)

__all__ = [
    "DicomViewer",
    "clear_measurements",
    "dicom_viewer",
    "flip",
    "jump_to_slice",
    "play_cine",
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

ViewerMode = Literal["stack", "volume", "volume3d"]
Orientation = Literal["axial", "sagittal", "coronal", "acquisition"]


class DicomViewer(NoSSRComponent):
    """A Cornerstone3D viewport rendering DICOM images from DICOMweb.

    Supply either ``image_ids`` directly, or a DICOMweb triple
    (``wado_rs_root`` + ``study_instance_uid`` + ``series_instance_uid``) and
    let the component fetch the series metadata and build the imageIds itself.

    Changing ``active_tool``, ``window_width``/``window_center``, ``invert``,
    ``colormap`` or ``cine`` updates the live viewport in place. Changing the
    data, ``mode``, ``orientation``, ``tools`` or any identity prop rebuilds it.

    Multi-viewport layouts: give each viewport a distinct ``viewport_id``. To
    make them behave as one group — which is what tools such as ``Crosshairs``
    and ``ReferenceLines`` require — give them the *same* ``tool_group_id``. To
    share loaded pixel data between them, give them the same ``volume_id``.

    Example:
        ```python
        dicom_viewer(
            wado_rs_root=PUBLIC_DICOMWEB_ROOT,
            study_instance_uid=State.study_uid,
            series_instance_uid=State.series_uid,
            active_tool=State.tool,
            mode="stack",
            height="70vh",
            on_measurements_change=State.set_measurements,
        )
        ```

    """

    tag = "RxDicomViewer"
    is_default = True

    lib_dependencies: list[str] = list(CORNERSTONE_PACKAGES)

    # --- data ------------------------------------------------------------

    # Explicit Cornerstone imageIds (``wadors:`` or ``wadouri:``). When set, the DICOMweb props
    # below are ignored. See :meth:`~reflex_ohif_viewer.dicomweb.DicomWebClient.image_ids`.
    image_ids: rx.Var[list[str]] = rx.Var.create([])

    # WADO-RS root URL of the DICOMweb server.
    wado_rs_root: rx.Var[str] = rx.Var.create("")

    # Study to load.
    study_instance_uid: rx.Var[str] = rx.Var.create("")

    # Series to load.
    series_instance_uid: rx.Var[str] = rx.Var.create("")

    # Restrict the series to a single instance.
    sop_instance_uid: rx.Var[str] = rx.Var.create("")

    # Extra request headers for the DICOMweb server, typically ``{"Authorization": "Bearer ..."}``.
    # Applied to metadata *and* frame requests for every imageId under ``wado_rs_root``.
    headers: rx.Var[dict[str, str]] = rx.Var.create({})

    # --- identity --------------------------------------------------------

    # Unique id for this viewport. Also the key under which the imperative API is registered, so
    # pass it to :func:`viewer_call` and friends.
    viewport_id: rx.Var[str] = rx.Var.create("rx-dicom-viewport")

    # Rendering engine id. Viewports sharing an engine share a WebGL context, which is usually what
    # you want on one page.
    rendering_engine_id: rx.Var[str] = rx.Var.create("rx-dicom-rendering-engine")

    # Tool group id. Defaults to ``f"{viewport_id}-tools"``. Share it across viewports for linked
    # tools such as ``Crosshairs``.
    tool_group_id: rx.Var[str] = rx.Var.create("")

    # Volume id, for ``mode="volume"``. Share it across viewports so the volume is decoded once and
    # reused (the MPR pattern).
    volume_id: rx.Var[str] = rx.Var.create("")

    # --- rendering -------------------------------------------------------

    # ``stack`` (2D frame-by-frame), ``volume`` (reformatted MPR plane) or ``volume3d`` (volume
    # rendering).
    mode: rx.Var[str] = rx.Var.create("stack")

    # Reformat plane for ``mode="volume"``.
    orientation: rx.Var[str] = rx.Var.create("axial")

    # Viewport background as ``[r, g, b]`` from 0 to 1.
    background: rx.Var[list[float]] = rx.Var.create([0.0, 0.0, 0.0])

    # Frame to open on. ``-1`` opens the middle of the stack.
    initial_image_index: rx.Var[int] = rx.Var.create(-1)

    # Explicit VOI range, ``{"lower": ..., "upper": ...}``. Takes precedence over ``window_width`` /
    # ``window_center``.
    voi_range: rx.Var[dict[str, float]] = rx.Var.create({})

    # Window width. Ignored when ``0``.
    window_width: rx.Var[float] = rx.Var.create(0.0)

    # Window center.
    window_center: rx.Var[float] = rx.Var.create(0.0)

    # Invert the grayscale ramp.
    invert: rx.Var[bool] = rx.Var.create(False)

    # Colormap name, e.g. ``"Inferno (matplotlib)"``. Empty means grayscale.
    colormap: rx.Var[str] = rx.Var.create("")

    # Volume-rendering preset for ``mode="volume3d"``, e.g. ``"CT-Bone"``.
    preset: rx.Var[str] = rx.Var.create("")

    # Slab thickness in millimetres for ``mode="volume"``.
    slab_thickness: rx.Var[float] = rx.Var.create(0.0)

    # --- tools -----------------------------------------------------------

    # Tools to register in the tool group. Empty uses
    # :data:`~reflex_ohif_viewer.constants.DEFAULT_TOOLS`.
    tools: rx.Var[list[str]] = rx.Var.create([])

    # The tool bound to the primary (left) mouse button. Right-drag is always zoom, middle-drag and
    # Ctrl+drag are pan, the wheel and Alt+drag scroll.
    active_tool: rx.Var[str] = rx.Var.create("WindowLevel")

    # --- runtime ---------------------------------------------------------

    # Frame-decode worker count. ``0`` uses half the hardware concurrency. Values above 3 are known
    # to misbehave on some Windows hosts.
    max_web_workers: rx.Var[int] = rx.Var.create(0)

    # Directory serving the codec ``.wasm`` files, e.g. ``"/cs-wasm/"``. Set this if frame decoding
    # fails with ``WebAssembly.instantiate(): expected magic word 00 61 73 6d, found 3c 21 64 6f`` —
    # that error means the bundler served ``index.html`` instead of the codec. See
    # :class:`~reflex_ohif_viewer.plugin.CornerstonePlugin`, which copies them and sets this for
    # you.
    wasm_base_path: rx.Var[str] = rx.Var.create("")

    # Auto-play the stack as a cine loop.
    cine: rx.Var[bool] = rx.Var.create(False)

    # Cine frame rate.
    cine_frames_per_second: rx.Var[int] = rx.Var.create(24)

    # Loop the cine playback.
    cine_loop: rx.Var[bool] = rx.Var.create(True)

    # --- presentation ----------------------------------------------------

    # Draw the four-corner DICOM overlay (patient, study, series, W/L, zoom).
    show_overlay: rx.Var[bool] = rx.Var.create(True)

    # Show the built-in loading indicator.
    show_loading_indicator: rx.Var[bool] = rx.Var.create(True)

    # Overlay text colour.
    overlay_color: rx.Var[str] = rx.Var.create("#9ae6b4")

    # --- events ----------------------------------------------------------

    # Fired once the first image is displayed. Receives a dict with ``viewportId``, ``toolGroupId``,
    # ``numImages``, ``index``, ``mode`` and the patient/study/series strings read from the DICOM
    # metadata.
    on_viewer_ready: rx.EventHandler[lambda info: [info]]

    # Fired on every frame change. Receives ``{"index": int, "total": int}``.
    on_slice_change: rx.EventHandler[lambda info: [info]]

    # Fired when window/level changes. Receives ``{"windowWidth": float, "windowCenter": float}``.
    on_voi_change: rx.EventHandler[lambda info: [info]]

    # Fired whenever the annotation set changes. Receives the full list of measurements, each
    # ``{"uid", "toolName", "label", "stats", ...}``.
    on_measurements_change: rx.EventHandler[lambda items: [items]]

    # Fired when an annotation is completed.
    on_annotation_added: rx.EventHandler[lambda annotation: [annotation]]

    # Fired when an annotation is edited.
    on_annotation_modified: rx.EventHandler[lambda annotation: [annotation]]

    # Fired when an annotation is deleted.
    on_annotation_removed: rx.EventHandler[lambda annotation: [annotation]]

    # Fired as frames arrive. Receives ``{"loaded": int, "total": int}``. Chatty on large series —
    # only wire it up if you show a progress bar.
    on_load_progress: rx.EventHandler[lambda progress: [progress]]

    # Fired when setup or loading fails. Receives the error message.
    on_error: rx.EventHandler[lambda message: [message]]

    @classmethod
    def create(cls, *children, **props) -> rx.Component:
        """Create the component after validating tool names.

        Args:
            *children: Ignored; the viewport manages its own DOM children.
            **props: Component props.

        Returns:
            The configured component.

        Raises:
            ValueError: If ``tools`` or ``active_tool`` names a tool this
                component cannot register. Catching the typo here beats a
                silent console warning at runtime.

        """
        tools = props.get("tools")
        if isinstance(tools, (list, tuple)):
            unknown = [tool for tool in tools if isinstance(tool, str) and tool not in ALL_TOOLS]
            if unknown:
                msg = (
                    f"Unknown Cornerstone tool(s): {', '.join(unknown)}. "
                    f"Supported tools: {', '.join(sorted(ALL_TOOLS))}"
                )
                raise ValueError(msg)
        active = props.get("active_tool")
        if isinstance(active, str) and active not in ALL_TOOLS:
            msg = f"Unknown active_tool {active!r}. Supported tools: {', '.join(sorted(ALL_TOOLS))}"
            raise ValueError(msg)

        component = super().create(*children, **props)
        component.library = dicom_viewer_library()
        return component


dicom_viewer = DicomViewer.create


# --------------------------------------------------------------------------- #
# Imperative API
# --------------------------------------------------------------------------- #
#
# Each mounted viewport registers itself on ``window.__rxDicomViewers`` under
# its ``viewport_id``. These helpers return Reflex event specs that call into
# it, so a backend event handler can drive the viewport without a round trip
# through props.


def viewer_call(viewport_id: str, method: str, *args: Any) -> rx.event.EventSpec:
    """Call a method on a mounted viewport's imperative API.

    Args:
        viewport_id: The ``viewport_id`` of the target viewport.
        method: The API method name.
        *args: JSON-serialisable arguments.

    Returns:
        An event spec suitable for returning from an event handler or wiring
        to a component event trigger.

    Example:
        ```python
        class State(rx.State):
            @rx.event
            def go_to_first_slice(self):
                return viewer_call("main", "jumpToSlice", 0)
        ```

    """
    payload = ", ".join(
        str(arg) if isinstance(arg, rx.Var) else rx.Var.create(arg).json() for arg in args
    )
    return rx.call_script(
        f"window.__rxDicomViewers?.[{rx.Var.create(viewport_id).json()}]?.{method}?.({payload})"
    )


def set_tool(viewport_id: str, tool: str) -> rx.event.EventSpec:
    """Bind ``tool`` to the primary mouse button.

    Args:
        viewport_id: The target viewport.
        tool: A tool name from
            :data:`~reflex_ohif_viewer.constants.ALL_TOOLS`.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "setTool", tool)


def reset_camera(viewport_id: str) -> rx.event.EventSpec:
    """Reset pan, zoom and rotation to the initial camera.

    Args:
        viewport_id: The target viewport.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "resetCamera")


def reset_properties(viewport_id: str) -> rx.event.EventSpec:
    """Reset window/level, inversion and colormap to the image defaults.

    Args:
        viewport_id: The target viewport.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "resetProperties")


def jump_to_slice(viewport_id: str, index: int) -> rx.event.EventSpec:
    """Jump to a frame by index. Negative indices count from the end.

    Args:
        viewport_id: The target viewport.
        index: The frame index.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "jumpToSlice", index)


def scroll(viewport_id: str, delta: int = 1) -> rx.event.EventSpec:
    """Scroll the stack by ``delta`` frames.

    Args:
        viewport_id: The target viewport.
        delta: Frames to advance; negative scrolls backwards.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "scroll", delta)


def set_window(viewport_id: str, width: float, center: float) -> rx.event.EventSpec:
    """Set window width and center.

    Args:
        viewport_id: The target viewport.
        width: Window width.
        center: Window center.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "setWindow", width, center)


def window_preset_range(preset: str) -> tuple[float, float]:
    """Look up a named window preset.

    Args:
        preset: A key of
            :data:`~reflex_ohif_viewer.constants.WINDOW_PRESETS`.

    Returns:
        The ``(window_width, window_center)`` pair.

    Raises:
        KeyError: If the preset is unknown.

    """
    if preset not in WINDOW_PRESETS:
        msg = f"Unknown window preset {preset!r}. Known: {', '.join(WINDOW_PRESETS)}"
        raise KeyError(msg)
    return WINDOW_PRESETS[preset]


def set_window_preset(viewport_id: str, preset: str) -> rx.event.EventSpec:
    """Apply a named window preset such as ``"CT Lung"``.

    Args:
        viewport_id: The target viewport.
        preset: A key of
            :data:`~reflex_ohif_viewer.constants.WINDOW_PRESETS`.

    Returns:
        The event spec.

    """
    width, center = window_preset_range(preset)
    return set_window(viewport_id, width, center)


def set_colormap(viewport_id: str, colormap: str) -> rx.event.EventSpec:
    """Apply a colormap, or clear it with an empty string.

    Args:
        viewport_id: The target viewport.
        colormap: A name from
            :data:`~reflex_ohif_viewer.constants.COLORMAPS`.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "setColormap", colormap)


def set_zoom(viewport_id: str, zoom: float) -> rx.event.EventSpec:
    """Set the zoom factor.

    Args:
        viewport_id: The target viewport.
        zoom: The zoom factor, where ``1.0`` fits the image.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "setZoom", zoom)


def rotate(viewport_id: str, degrees: float) -> rx.event.EventSpec:
    """Set the in-plane rotation in degrees.

    Args:
        viewport_id: The target viewport.
        degrees: Absolute rotation.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "rotate", degrees)


def flip(viewport_id: str, horizontal: bool = False, vertical: bool = False) -> rx.event.EventSpec:
    """Toggle horizontal and/or vertical flip.

    Args:
        viewport_id: The target viewport.
        horizontal: Toggle the horizontal flip.
        vertical: Toggle the vertical flip.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "flip", {"horizontal": horizontal, "vertical": vertical})


def play_cine(
    viewport_id: str, frames_per_second: int = 24, loop: bool = True
) -> rx.event.EventSpec:
    """Start cine playback.

    Args:
        viewport_id: The target viewport.
        frames_per_second: Playback rate.
        loop: Whether to loop at the end of the stack.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "playCine", frames_per_second, loop)


def stop_cine(viewport_id: str) -> rx.event.EventSpec:
    """Stop cine playback.

    Args:
        viewport_id: The target viewport.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "stopCine")


def clear_measurements(viewport_id: str) -> rx.event.EventSpec:
    """Delete every annotation, then re-emit ``on_measurements_change``.

    Args:
        viewport_id: The target viewport.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "clearMeasurements")


def remove_measurement(viewport_id: str, uid: str) -> rx.event.EventSpec:
    """Delete one annotation by its UID.

    Args:
        viewport_id: The target viewport.
        uid: The annotation UID, as reported by ``on_measurements_change``.

    Returns:
        The event spec.

    """
    return viewer_call(viewport_id, "removeMeasurement", uid)


#: Re-exported so callers can build a default toolbar without a second import.
DEFAULT_TOOLBAR: tuple[str, ...] = DEFAULT_TOOLS
