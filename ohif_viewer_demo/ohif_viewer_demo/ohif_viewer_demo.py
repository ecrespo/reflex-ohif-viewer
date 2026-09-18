"""reflex-ohif-viewer demo application."""

from __future__ import annotations

import reflex as rx

from .pages import deploy, mpr, native, ohif, overview
from .state import ViewerState

app = rx.App()

app.add_page(
    overview.index,
    route="/",
    title="reflex-ohif-viewer",
    description="OHIF Viewer and Cornerstone3D DICOM components for Reflex.",
)
app.add_page(
    native.index,
    route="/native",
    title="Native viewport · reflex-ohif-viewer",
    on_load=ViewerState.load_series,
)
app.add_page(
    mpr.index,
    route="/mpr",
    title="MPR · reflex-ohif-viewer",
    on_load=ViewerState.load_series,
)
app.add_page(ohif.index, route="/ohif", title="OHIF iframe · reflex-ohif-viewer")
app.add_page(deploy.index, route="/deploy", title="Deploy OHIF · reflex-ohif-viewer")
