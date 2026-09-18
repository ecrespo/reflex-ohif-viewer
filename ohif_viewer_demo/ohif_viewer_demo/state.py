"""Shared application state for the reflex-ohif-viewer demo."""

from __future__ import annotations

import dataclasses
import os

import reflex as rx
from reflex_ohif_viewer import (
    DEMO_STUDIES,
    PUBLIC_DICOMWEB_ROOT,
    DicomWebClient,
    DicomWebError,
)

#: Slug of the study selected when the app first loads.
DEFAULT_STUDY = "chest-ct"

#: Where the demo looks for DICOM. Override it to point the demo at your own
#: PACS without editing this file:
#:
#:     OHIF_DEMO_DICOMWEB_ROOT=https://pacs.internal/dicom-web reflex run
DEFAULT_ROOT = os.environ.get("OHIF_DEMO_DICOMWEB_ROOT", PUBLIC_DICOMWEB_ROOT)

#: A study UID to open instead of the built-in demo studies, for the same
#: reason. Leave unset to use the public demo studies.
DEFAULT_STUDY_UID = os.environ.get("OHIF_DEMO_STUDY_UID", "")


@dataclasses.dataclass
class Series:
    """One row of the series picker.

    Attributes:
        uid: The SeriesInstanceUID.
        modality: The series modality.
        number: The series number, as text.
        description: The series description.
        instances: How many instances the series holds.

    """

    uid: str
    modality: str
    number: str
    description: str
    instances: int


@dataclasses.dataclass
class Measurement:
    """One annotation reported by the viewport.

    Attributes:
        uid: The annotation UID.
        tool: The tool that created it.
        value: The primary measured value, pre-formatted.

    """

    uid: str
    tool: str
    value: str


def _format_stats(stats: dict) -> str:
    """Turn a Cornerstone ``cachedStats`` mapping into one readable line.

    Args:
        stats: The flattened statistics from the annotation.

    Returns:
        A short human-readable summary, or an empty string.

    """
    unit = str(stats.get("unit", "") or "")
    area_unit = str(stats.get("areaUnit", "") or "")
    parts: list[str] = []
    if "length" in stats:
        parts.append(f"{float(stats['length']):.1f} {unit or 'mm'}")
    if "area" in stats:
        parts.append(f"area {float(stats['area']):.1f} {area_unit or 'mm²'}")
    if "mean" in stats:
        parts.append(f"mean {float(stats['mean']):.1f}")
    if "stdDev" in stats:
        parts.append(f"sd {float(stats['stdDev']):.1f}")
    if "angle" in stats:
        parts.append(f"{float(stats['angle']):.1f}°")
    if "value" in stats:
        parts.append(f"{float(stats['value']):.1f}")
    return " · ".join(parts)


class ViewerState(rx.State):
    """Everything the demo pages read and write.

    The series list is fetched server-side with
    :class:`~reflex_ohif_viewer.dicomweb.DicomWebClient`, which is the point of
    shipping a Python DICOMweb client alongside the components: the study
    browser is ordinary Reflex state, not something hidden inside the viewer.
    """

    # --- data source -----------------------------------------------------
    dicomweb_root: str = DEFAULT_ROOT
    study_slug: str = DEFAULT_STUDY
    study_uid: str = DEFAULT_STUDY_UID or DEMO_STUDIES[DEFAULT_STUDY].study_instance_uid
    series: list[Series] = []
    series_uid: str = ""
    loading: bool = False
    load_error: str = ""

    # --- viewport --------------------------------------------------------
    mode: str = "stack"
    active_tool: str = "WindowLevel"
    window_preset: str = "CT Soft Tissue"
    window_width: float = 400.0
    window_center: float = 40.0
    colormap: str = ""
    invert: bool = False
    cine: bool = False
    show_overlay: bool = True

    # --- reported by the viewport ---------------------------------------
    ready: bool = False
    viewer_summary: str = ""
    slice_index: int = 0
    slice_total: int = 0
    measurements: list[Measurement] = []
    viewer_error: str = ""

    # --- OHIF iframe -----------------------------------------------------
    ohif_base_url: str = ""
    ohif_mode: str = "viewer"
    ohif_hanging_protocol: str = ""
    ohif_url: str = ""

    @rx.var
    def study_options(self) -> list[str]:
        """Labels for the study selector.

        Returns:
            One label per demo study.

        """
        return [f"{slug} — {study.description}" for slug, study in DEMO_STUDIES.items()]

    @rx.var
    def selected_study_label(self) -> str:
        """The label of the currently selected study.

        Returns:
            The matching label, or an empty string.

        """
        study = DEMO_STUDIES.get(self.study_slug)
        return f"{self.study_slug} — {study.description}" if study else ""

    @rx.var
    def series_labels(self) -> list[str]:
        """Labels for the series selector.

        Returns:
            One label per series in the loaded study.

        """
        return [
            f"{item.modality} · #{item.number} · {item.description or 'no description'}"
            f" ({item.instances})"
            for item in self.series
        ]

    @rx.var
    def selected_series_label(self) -> str:
        """The label of the currently selected series.

        Returns:
            The matching label, or an empty string.

        """
        for item, label in zip(self.series, self.series_labels, strict=False):
            if item.uid == self.series_uid:
                return label
        return ""

    @rx.var
    def slice_caption(self) -> str:
        """A short caption for the slice position.

        Returns:
            Text such as ``"Image 12 / 135"``.

        """
        if not self.slice_total:
            return "—"
        return f"Image {self.slice_index + 1} / {self.slice_total}"

    @rx.var
    def measurement_count(self) -> int:
        """How many annotations the viewport currently holds.

        Returns:
            The annotation count.

        """
        return len(self.measurements)

    # --- events ----------------------------------------------------------

    @rx.event(background=True)
    async def load_series(self):
        """Fetch the series of the selected study from the DICOMweb server."""
        async with self:
            self.loading = True
            self.load_error = ""
            self.series = []
            self.series_uid = ""
            root = self.dicomweb_root
            study = self.study_uid

        try:
            client = DicomWebClient(root)
            found = client.search_series(study)
            rows = [
                Series(
                    uid=item.series_instance_uid,
                    modality=item.modality,
                    number=item.series_number,
                    description=item.series_description,
                    instances=item.number_of_instances,
                )
                for item in found
                # Structured reports and RT objects have no renderable frames.
                if item.modality not in ("SR", "RTSTRUCT", "RTPLAN", "RTDOSE", "PR", "KO")
            ]
            async with self:
                self.series = rows
                self.series_uid = rows[0].uid if rows else ""
                self.loading = False
                if not rows:
                    self.load_error = "This study has no renderable image series."
        except DicomWebError as exc:
            async with self:
                self.loading = False
                self.load_error = str(exc)

    @rx.event
    def select_study(self, label: str):
        """Change the active study and reload its series.

        Args:
            label: A label produced by :meth:`study_options`.

        Returns:
            The follow-up event that loads the series.

        """
        slug = label.split(" — ", 1)[0]
        if slug in DEMO_STUDIES:
            self.study_slug = slug
            self.study_uid = DEMO_STUDIES[slug].study_instance_uid
        self.reset_viewer_report()
        return ViewerState.load_series

    @rx.event
    def select_series(self, label: str):
        """Change the active series.

        Args:
            label: A label produced by :meth:`series_labels`.

        """
        for item, candidate in zip(self.series, self.series_labels, strict=False):
            if candidate == label:
                self.series_uid = item.uid
                break
        self.reset_viewer_report()

    @rx.event
    def set_root(self, value: str):
        """Point the demo at a different DICOMweb server.

        Args:
            value: The new WADO-RS / QIDO-RS root URL.

        Returns:
            The follow-up event that reloads the series.

        """
        self.dicomweb_root = value.strip()
        return ViewerState.load_series

    @rx.event
    def reset_viewer_report(self):
        """Clear everything the viewport reported about the previous series."""
        self.ready = False
        self.viewer_summary = ""
        self.slice_index = 0
        self.slice_total = 0
        self.measurements = []
        self.viewer_error = ""

    @rx.event
    def apply_window_preset(self, preset: str):
        """Apply a named window preset to the viewport.

        Args:
            preset: A key of ``WINDOW_PRESETS``.

        """
        from reflex_ohif_viewer import window_preset_range

        self.window_preset = preset
        self.window_width, self.window_center = window_preset_range(preset)

    @rx.event
    def on_viewer_ready(self, info: dict):
        """Record the viewport's startup report.

        Args:
            info: The payload from ``on_viewer_ready``.

        """
        self.ready = True
        self.viewer_error = ""
        self.slice_total = int(info.get("numImages", 0) or 0)
        self.slice_index = int(info.get("index", 0) or 0)
        patient = info.get("patientName", "") or "unknown patient"
        modality = info.get("modality", "") or "?"
        self.viewer_summary = (
            f"{patient} · {modality} · {self.slice_total} images · {info.get('mode', '')}"
        )

    @rx.event
    def on_slice_change(self, info: dict):
        """Track the displayed frame.

        Args:
            info: ``{"index": int, "total": int}``.

        """
        self.slice_index = int(info.get("index", 0) or 0)
        self.slice_total = int(info.get("total", self.slice_total) or 0)

    @rx.event
    def on_voi_change(self, info: dict):
        """Track window/level changes made with the mouse.

        Args:
            info: ``{"windowWidth": float, "windowCenter": float}``.

        """
        self.window_width = round(float(info.get("windowWidth", 0) or 0), 1)
        self.window_center = round(float(info.get("windowCenter", 0) or 0), 1)
        self.window_preset = "Custom"

    @rx.event
    def on_measurements_change(self, items: list[dict]):
        """Replace the measurement table with the viewport's annotation set.

        Args:
            items: The annotations reported by the viewport.

        """
        self.measurements = [
            Measurement(
                uid=str(item.get("uid", "")),
                tool=str(item.get("toolName", "")),
                value=_format_stats(item.get("stats", {}) or {}) or "—",
            )
            for item in items
        ]

    @rx.event
    def on_viewer_error(self, message: str):
        """Surface a viewport failure in the UI.

        Args:
            message: The error message.

        """
        self.viewer_error = message
        self.ready = False

    @rx.event
    def set_mode(self, value: str | list[str]):
        """Switch between stack, volume and 3D rendering.

        Args:
            value: ``stack``, ``volume`` or ``volume3d``. Reflex's segmented
                control types its value as a union, hence the signature.

        """
        self.mode = value if isinstance(value, str) else (value[0] if value else "stack")
        self.reset_viewer_report()

    @rx.event
    def set_active_tool(self, value: str):
        """Bind a tool to the primary mouse button.

        Args:
            value: A Cornerstone tool name.

        """
        self.active_tool = value

    @rx.event
    def set_colormap(self, value: str):
        """Apply or clear the viewport colormap.

        Args:
            value: A colormap name, or ``"(none)"`` to clear it.

        """
        self.colormap = "" if value == "(none)" else value

    @rx.event
    def set_invert(self, value: bool):
        """Toggle the inverted grayscale ramp.

        Args:
            value: Whether to invert.

        """
        self.invert = value

    @rx.event
    def set_cine(self, value: bool):
        """Toggle cine playback.

        Args:
            value: Whether to play.

        """
        self.cine = value

    @rx.event
    def set_show_overlay(self, value: bool):
        """Toggle the four-corner DICOM overlay.

        Args:
            value: Whether to draw it.

        """
        self.show_overlay = value

    @rx.event
    def on_ohif_url_change(self, url: str):
        """Record the URL the OHIF iframe navigated to.

        Args:
            url: The computed OHIF URL.

        """
        self.ohif_url = url
