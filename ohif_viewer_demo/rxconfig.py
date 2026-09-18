"""Reflex configuration for the reflex-ohif-viewer demo app."""

import reflex as rx
from reflex_ohif_viewer import CornerstonePlugin

config = rx.Config(
    app_name="ohif_viewer_demo",
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="dark",
                accent_color="iris",
                gray_color="slate",
                radius="medium",
            )
        ),
        # Copies the Cornerstone3D WASM codecs into public/ and keeps Vite's
        # dependency pre-bundler away from the DICOM image loader's workers.
        CornerstonePlugin(),
    ],
)
