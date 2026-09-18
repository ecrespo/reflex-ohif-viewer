"""Constants, enumerations and verified demo data for ``reflex-ohif-viewer``.

Every value in this module was checked against upstream source at the versions
recorded in :data:`VERSIONS` rather than copied from documentation, because the
OHIF and Cornerstone3D docs lag their code by several minor versions.
"""

from __future__ import annotations

from typing import Final, Literal

#: Upstream versions this package was written and verified against.
VERSIONS: Final[dict[str, str]] = {
    "cornerstone3d": "5.10.6",
    "ohif_viewer": "3.13.8",
    "ohif_docker_image": "ohif/app:v3.13.8",
}

# --------------------------------------------------------------------------- #
# npm packages
# --------------------------------------------------------------------------- #

#: npm packages required by the native Cornerstone3D viewport.
#:
#: ``@cornerstonejs/metadata`` and ``@cornerstonejs/utils`` were split out of
#: ``core`` in Cornerstone 5.x and are hard peer dependencies, so they are
#: listed explicitly instead of being left to the package manager.
CORNERSTONE_PACKAGES: Final[tuple[str, ...]] = (
    "@cornerstonejs/core@5.10.6",
    "@cornerstonejs/tools@5.10.6",
    "@cornerstonejs/dicom-image-loader@5.10.6",
    "@cornerstonejs/metadata@5.10.6",
    "@cornerstonejs/utils@5.10.6",
    "dicom-parser@1.8.21",
    "dicomweb-client@0.11.3",
)

#: Packages that ship the WASM codecs the DICOM image loader decodes frames
#: with. They arrive transitively; they are named here so the Vite plugin can
#: find their ``.wasm`` files and copy them into ``public/``.
CORNERSTONE_CODEC_PACKAGES: Final[tuple[str, ...]] = (
    "@cornerstonejs/codec-charls",
    "@cornerstonejs/codec-libjpeg-turbo-8bit",
    "@cornerstonejs/codec-openjpeg",
    "@cornerstonejs/codec-openjph",
)

# --------------------------------------------------------------------------- #
# Cornerstone3D tools
# --------------------------------------------------------------------------- #

ToolName = Literal[
    "Pan",
    "Zoom",
    "WindowLevel",
    "WindowLevelRegion",
    "StackScroll",
    "PlanarRotate",
    "TrackballRotate",
    "VolumeRotateMouseWheel",
    "Magnify",
    "AdvancedMagnify",
    "DragProbe",
    "Length",
    "Height",
    "Probe",
    "RectangleROI",
    "EllipticalROI",
    "CircleROI",
    "Bidirectional",
    "Angle",
    "CobbAngle",
    "ArrowAnnotate",
    "PlanarFreehandROI",
    "SplineROI",
    "LivewireContour",
    "KeyImage",
    "Label",
    "Eraser",
    "Crosshairs",
    "ReferenceLines",
    "ScaleOverlay",
    "OrientationMarker",
    "Brush",
    "RectangleScissor",
    "CircleScissor",
    "SphereScissor",
    "PaintFill",
    "SegmentSelect",
]

#: Tools that move the camera or the stack rather than drawing anything.
NAVIGATION_TOOLS: Final[tuple[str, ...]] = (
    "Pan",
    "Zoom",
    "WindowLevel",
    "WindowLevelRegion",
    "StackScroll",
    "PlanarRotate",
    "TrackballRotate",
    "VolumeRotateMouseWheel",
    "Magnify",
    "AdvancedMagnify",
    "DragProbe",
)

#: Tools that create measurable annotations.
ANNOTATION_TOOLS: Final[tuple[str, ...]] = (
    "Length",
    "Height",
    "Probe",
    "RectangleROI",
    "EllipticalROI",
    "CircleROI",
    "Bidirectional",
    "Angle",
    "CobbAngle",
    "ArrowAnnotate",
    "PlanarFreehandROI",
    "SplineROI",
    "LivewireContour",
    "KeyImage",
    "Label",
    "Eraser",
)

#: Tools that draw reference overlays rather than responding to a mouse button.
OVERLAY_TOOLS: Final[tuple[str, ...]] = (
    "Crosshairs",
    "ReferenceLines",
    "ScaleOverlay",
    "OrientationMarker",
)

#: Segmentation editing tools.
SEGMENTATION_TOOLS: Final[tuple[str, ...]] = (
    "Brush",
    "RectangleScissor",
    "CircleScissor",
    "SphereScissor",
    "PaintFill",
    "SegmentSelect",
)

#: Every tool this component knows how to register.
ALL_TOOLS: Final[tuple[str, ...]] = (
    NAVIGATION_TOOLS + ANNOTATION_TOOLS + OVERLAY_TOOLS + SEGMENTATION_TOOLS
)

#: A sensible default tool group: navigation plus the common measurements.
DEFAULT_TOOLS: Final[tuple[str, ...]] = (
    "WindowLevel",
    "Pan",
    "Zoom",
    "StackScroll",
    "Length",
    "RectangleROI",
    "EllipticalROI",
    "CircleROI",
    "Bidirectional",
    "Angle",
    "ArrowAnnotate",
    "Probe",
    "PlanarFreehandROI",
    "Magnify",
    "Eraser",
)

# --------------------------------------------------------------------------- #
# Window / level presets
# --------------------------------------------------------------------------- #

#: Common CT window presets as ``(window_width, window_center)`` in Hounsfield
#: units, plus a few non-CT defaults.
WINDOW_PRESETS: Final[dict[str, tuple[float, float]]] = {
    "CT Soft Tissue": (400, 40),
    "CT Lung": (1500, -600),
    "CT Bone": (2000, 300),
    "CT Brain": (80, 40),
    "CT Liver": (150, 30),
    "CT Mediastinum": (350, 50),
    "CT Angio": (600, 300),
    "CT Abdomen": (350, 50),
    "PET": (10, 5),
    "MR Default": (1000, 500),
}

#: Colormaps accepted by ``viewport.setProperties({colormap: {name}})``.
COLORMAPS: Final[tuple[str, ...]] = (
    "Grayscale",
    "hsv",
    "Inferno (matplotlib)",
    "Viridis (matplotlib)",
    "Plasma (matplotlib)",
    "Magma (matplotlib)",
    "Black-Body Radiation",
    "Cool to Warm",
    "Rainbow Desaturated",
    "X Ray",
)

#: Volume-rendering presets usable with ``mode="volume3d"``.
VOLUME_RENDERING_PRESETS: Final[tuple[str, ...]] = (
    "CT-AAA",
    "CT-AAA2",
    "CT-Bone",
    "CT-Bones",
    "CT-Cardiac",
    "CT-Cardiac2",
    "CT-Cardiac3",
    "CT-Chest-Contrast-Enhanced",
    "CT-Chest-Vessels",
    "CT-Coronary-Arteries",
    "CT-Coronary-Arteries-2",
    "CT-Coronary-Arteries-3",
    "CT-Cropped-Volume-Bone",
    "CT-Fat",
    "CT-Liver-Vasculature",
    "CT-Lung",
    "CT-MIP",
    "CT-Muscle",
    "CT-Pulmonary-Arteries",
    "CT-Soft-Tissue",
    "MR-Angio",
    "MR-Default",
    "MR-MIP",
    "MR-T2-Brain",
)

# --------------------------------------------------------------------------- #
# OHIF Viewer v3
# --------------------------------------------------------------------------- #

OhifMode = Literal[
    "viewer",
    "segmentation",
    "tmtv",
    "microscopy",
    "dynamic-volume",
    "usAnnotation",
    "basic",
    "dev",
    "basic-test",
]

#: OHIF mode route segment -> human readable name.
#:
#: The route segment is a mode's ``routeName``, not its package id. The "basic
#: viewer" everyone means lives at ``/viewer`` and comes from
#: ``@ohif/mode-longitudinal``; there is no ``basic-viewer`` route.
OHIF_MODES: Final[dict[str, str]] = {
    "viewer": "Basic Viewer (longitudinal)",
    "segmentation": "Segmentation",
    "tmtv": "Total Metabolic Tumor Volume",
    "microscopy": "Microscopy",
    "dynamic-volume": "Preclinical 4D",
    "usAnnotation": "Ultrasound Pleura B-line",
    "basic": "Non-longitudinal Basic",
    "dev": "Basic Dev Viewer",
    "basic-test": "Basic Test Mode",
}

#: Hanging protocol ids registered by the stock OHIF extensions.
OHIF_HANGING_PROTOCOLS: Final[dict[str, str]] = {
    "default": "Default (single viewport)",
    "@ohif/hpCompare": "Comparison",
    "@ohif/hpMammo": "Mammography",
    "@ohif/hpScale": "Scale",
    "@ohif/mnGrid": "Grid (multi-series)",
    "@ohif/mnGrid8": "Grid 8-up",
    "mpr": "MPR (axial/sagittal/coronal)",
    "mprAnd3DVolumeViewport": "MPR + 3D volume",
    "fourUp": "Four up",
    "main3D": "3D volume",
    "primaryAxial": "Primary axial",
    "only3D": "3D only",
    "primary3D": "Primary + 3D",
    "frameView": "Frame view",
}

#: OHIF study-list (WorkList) query keys, from
#: ``platform/app/src/utils/studyListFilterContract.ts``.
OHIF_WORKLIST_KEYS: Final[tuple[str, ...]] = (
    "patientName",
    "mrn",
    "description",
    "accession",
    "modalities",
    "startDate",
    "endDate",
    "sortBy",
    "sortDirection",
    "pageNumber",
    "resultsPerPage",
)

# --------------------------------------------------------------------------- #
# Public demo data (no authentication required)
# --------------------------------------------------------------------------- #

#: The DICOMweb root used by viewer.ohif.org and by the Cornerstone3D examples.
#: Static DICOMweb served from CloudFront, so ``static_wado=True`` is required
#: when pointing OHIF at it.
PUBLIC_DICOMWEB_ROOT: Final[str] = "https://d14fa38qiwhyfd.cloudfront.net/dicomweb"

#: A second public root used by several Cornerstone3D segmentation examples.
PUBLIC_DICOMWEB_ROOT_ALT: Final[str] = "https://d33do7qe4w26qo.cloudfront.net/dicomweb"


class DemoStudy:
    """A public study on :data:`PUBLIC_DICOMWEB_ROOT`, with useful series.

    Attributes:
        study_instance_uid: The study UID to pass to OHIF or the viewport.
        description: What the study contains.
        series: Mapping of human label to SeriesInstanceUID.

    """

    def __init__(
        self,
        study_instance_uid: str,
        description: str,
        series: dict[str, str],
    ) -> None:
        """Initialise the demo study descriptor.

        Args:
            study_instance_uid: The study UID.
            description: A short human description.
            series: Mapping of label to SeriesInstanceUID.

        """
        self.study_instance_uid = study_instance_uid
        self.description = description
        self.series = series

    def __repr__(self) -> str:
        """Return a readable representation.

        Returns:
            A short debug string.

        """
        return f"DemoStudy({self.description!r}, {len(self.series)} series)"


#: PET/CT study used by ~175 Cornerstone3D examples; its ``CT IMAGES`` series is
#: the single most common Cornerstone3D reference series. Series counts and UIDs
#: verified against the live server on 2026-09-17.
DEMO_CHEST_CT: Final[DemoStudy] = DemoStudy(
    study_instance_uid="1.3.6.1.4.1.14519.5.2.1.7009.2403.334240657131972136850343327463",
    description="PET/CT (TCIA) — the Cornerstone3D reference study",
    series={
        "CT images (135)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.226151125820845824875394858561",
        "PET AC (135)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.879445243400782656317561081015",
        "PET NAC (135)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.196579865982768309054410462754",
        "Scout (1)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.285235930168924996436870336581",
    },
)

#: Whole-body PET/CT. Good for fusion, PET windowing and the OHIF ``tmtv`` mode.
DEMO_PET_CT: Final[DemoStudy] = DemoStudy(
    study_instance_uid="1.3.6.1.4.1.14519.5.2.1.7009.2403.871108593056125491804754960339",
    description="Whole-body PET/CT (TCIA) — 311-slice CT, PET AC and PET NAC",
    series={
        "CT images (311)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.367700692008930469189923116409",
        "PET AC (311)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.780462962868572737240023906400",
        "PET NAC (311)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.163066661055228905323984189931",
        "Scout (1)": "1.3.6.1.4.1.14519.5.2.1.7009.2403.168353129945747450419572751964",
    },
)

#: Multi-series abdominal CT. The study OHIF's own end-to-end suite uses most.
DEMO_ABDOMEN_CT: Final[DemoStudy] = DemoStudy(
    study_instance_uid="1.3.6.1.4.1.25403.345050719074.3824.20170125095438.5",
    description="Abdomen/lung CT — five reconstructions of one acquisition",
    series={
        "Body 3.0 CE (120)": "1.3.6.1.4.1.25403.345050719074.3824.20170125095438.11",
        "Lung 3.0 CE (117)": "1.3.6.1.4.1.25403.345050719074.3824.20170125095449.8",
        "Body 4.0 CE (86)": "1.3.6.1.4.1.25403.345050719074.3824.20170125095506.10",
        "Body 4.0 CE (56)": "1.3.6.1.4.1.25403.345050719074.3824.20170125095501.12",
        "2.0 (2)": "1.3.6.1.4.1.25403.345050719074.3824.20170125095438.6",
    },
)

#: PET/CT with an RTSTRUCT series, for radiotherapy contour overlays.
DEMO_RTSTRUCT: Final[DemoStudy] = DemoStudy(
    study_instance_uid="1.2.840.113619.2.290.3.3767434740.226.1600859119.501",
    description="PET/CT with RTSTRUCT contours",
    series={
        "CT Std (76)": "2.16.840.1.114362.1.12114306.25269253871.642214904.129.557",
        "CTAC (47)": "2.16.840.1.114362.1.12114306.25269253871.642214906.452.682",
        "PET AC192 (47)": "2.16.840.1.114362.1.12114306.25269253871.642214905.509.634",
        "PET NAC (47)": "2.16.840.1.114362.1.12114306.25269253871.642214903.266.509",
        "RTSTRUCT (1)": "2.16.840.1.114362.1.12114306.25269253871.642214907.120.729",
    },
)

#: All demo studies, keyed by a short slug.
DEMO_STUDIES: Final[dict[str, DemoStudy]] = {
    "chest-ct": DEMO_CHEST_CT,
    "pet-ct": DEMO_PET_CT,
    "abdomen-ct": DEMO_ABDOMEN_CT,
    "rtstruct": DEMO_RTSTRUCT,
}
