"""Frontend asset registration for ``reflex-ohif-viewer``.

``rx.asset(..., shared=True)`` symlinks a file that ships inside this Python
package into the compiling app's ``assets/external/`` directory and hands back
an ``importable_path`` (``$/public/...``) that a Reflex component can use as its
``library``. Every asset is registered from this one module so that all of them
land in the same directory and can import each other with relative paths.

Registration is deferred until a component is actually created: importing this
package must not write into whatever directory happens to be the working
directory.
"""

from __future__ import annotations

import reflex as rx

__all__ = ["dicom_viewer_library", "ohif_viewer_library"]

_cache: dict[str, str] = {}


def _register() -> None:
    """Link every shipped frontend file into the app's external assets."""
    if _cache:
        return
    # The runtime helper must be linked first: the two components import it
    # with a relative specifier once Vite resolves them.
    rx.asset("rxCornerstoneRuntime.js", shared=True)
    rx.asset("rxOhifUrl.js", shared=True)
    _cache["dicom_viewer"] = rx.asset("RxDicomViewer.jsx", shared=True).importable_path
    _cache["ohif_viewer"] = rx.asset("RxOhifViewer.jsx", shared=True).importable_path


def dicom_viewer_library() -> str:
    """Return the importable path of the Cornerstone3D viewport module.

    Returns:
        A ``$/public/...`` specifier usable as a Reflex component ``library``.

    """
    _register()
    return _cache["dicom_viewer"]


def ohif_viewer_library() -> str:
    """Return the importable path of the OHIF iframe module.

    Returns:
        A ``$/public/...`` specifier usable as a Reflex component ``library``.

    """
    _register()
    return _cache["ohif_viewer"]
