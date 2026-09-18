"""A Reflex plugin that makes Cornerstone3D's WASM codecs survive bundling.

``@cornerstonejs/dicom-image-loader`` decodes compressed DICOM frames in web
workers using four WebAssembly codecs. It loads them with the bundler-native
``new URL('...', import.meta.url)`` pattern, resolving the codec packages by
bare specifier. Vite's Rollup/Rolldown build resolves those, but its esbuild
dependency pre-bundler does not, so a dev server can end up serving
``index.html`` where a ``.wasm`` was expected. The symptom is unmistakable::

    CompileError: WebAssembly.instantiate(): expected magic word 00 61 73 6d,
    found 3c 21 64 6f

(``3c 21 64 6f`` is ``<!do`` — the start of an HTML document.)

This plugin removes the whole failure mode by taking the bundler out of the
loop: it copies the codec ``.wasm`` files into the app's ``public/`` directory
and points the loader at that URL prefix through
:attr:`~reflex_ohif_viewer.dicom_viewer.DicomViewer.wasm_base_path`. It also
patches ``vite.config.js`` so the loader is excluded from dependency
pre-bundling and workers are emitted as ES modules.

Register it in ``rxconfig.py``::

    from reflex_ohif_viewer import CornerstonePlugin

    config = rx.Config(
        app_name="my_app",
        plugins=[CornerstonePlugin()],
    )

The plugin is optional: the component works without it in a normal production
build. Add it when frame decoding fails, when you serve the app from a
sub-path, or when you want the codecs on your own CDN.
"""

from __future__ import annotations

import dataclasses
import shutil
from pathlib import Path
from typing import Any

from reflex.plugins.base import Plugin

from .constants import CORNERSTONE_CODEC_PACKAGES, CORNERSTONE_PACKAGES

__all__ = ["CornerstonePlugin"]

_VITE_CONFIG = "vite.config.js"
_MARKER = "reflex-ohif-viewer:cornerstone"

# The anchor is the first line of the object literal returned by
# `defineConfig`, which every Reflex 0.9 vite config template contains.
_ANCHOR = 'base: "'

#: Packages whose pre-bundled chunk would eagerly evaluate Node-only modules.
_NO_PREBUNDLE: tuple[str, ...] = (
    "@cornerstonejs/core",
    "@cornerstonejs/tools",
    "@cornerstonejs/dicom-image-loader",
    "@cornerstonejs/metadata",
    "@cornerstonejs/utils",
)

#: CommonJS leaf packages Cornerstone3D imports directly, which need interop.
_PREBUNDLE: tuple[str, ...] = (
    "dicom-parser",
    "fast-deep-equal",
    "seedrandom",
    "spark-md5",
    "loglevel",
    "ndarray",
    "utif",
    "lodash.clonedeep",
    "lodash.get",
    # dcmjs imports xmlbuilder2 for DICOM-XML. Its CommonJS entry needs interop,
    # and it subclasses Node's EventEmitter, which is why the browser
    # implementation of `events` is declared as a dependency below.
    "xmlbuilder2",
    # The four WASM codec wrappers are CommonJS as well, and the image loader
    # imports them by subpath, so the subpath is what has to be named here.
    "@cornerstonejs/codec-charls/decodewasmjs",
    "@cornerstonejs/codec-libjpeg-turbo-8bit/decodewasmjs",
    "@cornerstonejs/codec-openjpeg/decodewasmjs",
    "@cornerstonejs/codec-openjph/wasmjs",
)

#: Browser implementations of the Node built-ins Cornerstone's dependency tree
#: reaches. Declaring them as real packages makes Vite resolve the bare
#: specifier to a working module instead of externalising it to an empty stub.
_NODE_SHIMS: tuple[str, ...] = ("events@3.3.0",)


def _vite_patch(exclude: tuple[str, ...], include: tuple[str, ...]) -> str:
    """Build the config fragment injected into ``vite.config.js``.

    Two opposite adjustments are needed, for two different reasons.

    ``exclude`` keeps the Cornerstone packages out of dependency pre-bundling.
    Pre-bundling flattens a package and everything it can reach into one chunk,
    which is evaluated as a unit — so a Node-only module that Cornerstone only
    reaches down a code path the viewer never takes (``dcmjs`` → ``xmlbuilder2``
    → Node's ``events``) still runs at import time and throws
    ``Class extends value undefined is not a constructor or null``. Left
    unbundled, those modules are only evaluated if something actually imports
    them.

    ``include`` does the reverse for the small CommonJS leaf packages
    Cornerstone imports directly. Excluding their importer means Vite serves
    them raw, and a CommonJS module has no ES default export, hence
    ``does not provide an export named 'default'``. Naming them here gets them
    pre-bundled on their own, with interop, and without dragging a package tree
    along.

    Args:
        exclude: npm packages to keep out of dependency pre-bundling.
        include: npm packages to force through dependency pre-bundling.

    Returns:
        JavaScript object properties, ready to splice into the config literal.

    """
    excluded = ",\n      ".join(f'"{name}"' for name in exclude)
    included = ",\n      ".join(f'"{name}"' for name in include)
    return f"""// {_MARKER} — see reflex_ohif_viewer/plugin.py for why.
  optimizeDeps: {{
    exclude: [
      {excluded}
    ],
    include: [
      {included}
    ],
  }},
  assetsInclude: ["**/*.wasm"],
  worker: {{ format: "es" }},
  """


@dataclasses.dataclass
class CornerstonePlugin(Plugin):
    """Make the Cornerstone3D WASM codecs and web workers bundle reliably.

    Attributes:
        wasm_dir: Directory under ``public/`` to copy the codecs into. The
            matching URL prefix is ``/<wasm_dir>/``.
        copy_wasm: Copy the codec ``.wasm`` files into ``public/``. Turn this
            off if you serve them from a CDN and set ``wasm_base_path``
            yourself.
        patch_vite_config: Patch ``vite.config.js`` with the ``optimizeDeps``
            exclusions, ``assetsInclude`` and ES-module worker format.
        declare_dependencies: Add the Cornerstone npm packages to the app's
            ``package.json`` even on pages that do not use the viewport. Useful
            when you build the frontend ahead of time in CI.

    """

    wasm_dir: str = "cs-wasm"
    copy_wasm: bool = True
    patch_vite_config: bool = True
    declare_dependencies: bool = True

    @property
    def wasm_base_path(self) -> str:
        """The URL prefix to pass to ``dicom_viewer(wasm_base_path=...)``.

        Returns:
            A root-relative URL ending in a slash.

        """
        return f"/{self.wasm_dir.strip('/')}/"

    def get_frontend_dependencies(self, **context: Any) -> list[str]:
        """Declare the Cornerstone npm packages for the app.

        Args:
            **context: The Reflex plugin context (unused).

        Returns:
            The npm package specifiers, or an empty list when disabled.

        """
        if not self.declare_dependencies:
            return []
        return [*CORNERSTONE_PACKAGES, *_NODE_SHIMS]

    def pre_compile(self, **context: Any) -> None:
        """Register the ``vite.config.js`` patch before compilation.

        Args:
            **context: The Reflex pre-compile context.

        """
        if not self.patch_vite_config:
            return
        context["add_modify_task"](_VITE_CONFIG, self._patch_config)

    def _patch_config(self, content: str) -> str:
        """Splice the Cornerstone options into the Vite config literal.

        Args:
            content: The current ``vite.config.js`` text.

        Returns:
            The patched text, or the input unchanged when already patched or
            when the expected anchor is missing.

        """
        # Strip a block left by an earlier version of this plugin so an
        # upgrade is not silently ignored: Reflex keeps ``vite.config.js``
        # between compiles, so a stale patch would otherwise survive forever.
        marker_start = content.find(f"// {_MARKER}")
        if marker_start != -1:
            anchor_after = content.find(_ANCHOR, marker_start)
            if anchor_after == -1:
                return content
            content = content[:marker_start] + content[anchor_after:]
        if _ANCHOR not in content:
            # The upstream template changed. Failing the build over a
            # performance/robustness tweak would be worse than skipping it.
            print(
                "[reflex-ohif-viewer] could not patch vite.config.js "
                f"(anchor {_ANCHOR!r} not found); continuing without it. "
                "If DICOM decoding fails, pass wasm_base_path explicitly."
            )
            return content
        return content.replace(_ANCHOR, _vite_patch(_NO_PREBUNDLE, _PREBUNDLE) + _ANCHOR, 1)

    def post_compile(self, **context: Any) -> None:
        """Copy the codec ``.wasm`` files into the app's ``public/`` directory.

        Args:
            **context: The Reflex post-compile context.

        """
        if not self.copy_wasm:
            return
        self.copy_codecs(Path.cwd())

    def copy_codecs(self, app_root: Path) -> list[Path]:
        """Copy every codec ``.wasm`` file into ``.web/public/<wasm_dir>/``.

        Safe to call repeatedly; files are only rewritten when their size
        differs, so file watchers are not woken up on every compile.

        Args:
            app_root: The Reflex app root, i.e. the directory holding ``.web``.

        Returns:
            The destination paths that now exist.

        Raises:
            FileNotFoundError: Never — a missing ``node_modules`` is reported
                on stdout and treated as "nothing to do", because the first
                compile of a fresh app runs before the install.

        """
        node_modules = app_root / ".web" / "node_modules"
        destination = app_root / ".web" / "public" / self.wasm_dir.strip("/")
        if not node_modules.is_dir():
            return []

        destination.mkdir(parents=True, exist_ok=True)
        copied: list[Path] = []
        for package in CORNERSTONE_CODEC_PACKAGES:
            package_dir = node_modules.joinpath(*package.split("/"))
            if not package_dir.is_dir():
                continue
            for wasm in package_dir.rglob("*.wasm"):
                target = destination / wasm.name
                if target.exists() and target.stat().st_size == wasm.stat().st_size:
                    copied.append(target)
                    continue
                shutil.copy2(wasm, target)
                copied.append(target)

        if not copied:
            print(
                "[reflex-ohif-viewer] no Cornerstone codec .wasm files found under "
                f"{node_modules}. They are installed transitively with "
                "@cornerstonejs/dicom-image-loader; this is expected on the very "
                "first compile, before the frontend install runs."
            )
        return copied
