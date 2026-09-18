"""Tests for the Vite configuration patch and the WASM codec copy."""

from pathlib import Path

from reflex_ohif_viewer import CornerstonePlugin

# A stand-in for the part of Reflex's vite.config.js template the patch anchors
# on. The real template is larger, but this is the shape that matters.
VITE_TEMPLATE = """import { defineConfig } from "vite";

export default defineConfig((config) => ({
  base: "/",
  plugins: [reactRouter()],
}));
"""


def test_patch_inserts_before_the_base_option():
    patched = CornerstonePlugin()._patch_config(VITE_TEMPLATE)
    assert patched.index("optimizeDeps") < patched.index('base: "')
    assert "assetsInclude" in patched
    assert 'worker: { format: "es" }' in patched


def test_patch_excludes_the_cornerstone_packages_from_prebundling():
    patched = CornerstonePlugin()._patch_config(VITE_TEMPLATE)
    exclude = patched.split("exclude: [")[1].split("]")[0]
    for package in ("core", "tools", "dicom-image-loader", "metadata", "utils"):
        assert f'"@cornerstonejs/{package}"' in exclude


def test_patch_prebundles_the_commonjs_leaves():
    patched = CornerstonePlugin()._patch_config(VITE_TEMPLATE)
    include = patched.split("include: [")[1].split("]")[0]
    # These are the packages whose absence produced
    # "does not provide an export named 'default'" in a real build.
    for package in ("dicom-parser", "fast-deep-equal", "seedrandom", "xmlbuilder2"):
        assert f'"{package}"' in include
    # The image loader imports the codecs by subpath, so the subpath is what
    # Vite needs named.
    assert '"@cornerstonejs/codec-openjph/wasmjs"' in include


def test_patch_is_idempotent():
    plugin = CornerstonePlugin()
    once = plugin._patch_config(VITE_TEMPLATE)
    twice = plugin._patch_config(once)
    assert once == twice


def test_patch_replaces_a_block_left_by_an_older_version():
    # Reflex keeps vite.config.js between compiles, so an upgrade has to
    # overwrite the previous block rather than skip or duplicate it.
    stale = VITE_TEMPLATE.replace(
        'base: "',
        '// reflex-ohif-viewer:cornerstone — old\n  optimizeDeps: { exclude: ["stale"] },\n  base: "',
    )
    patched = CornerstonePlugin()._patch_config(stale)
    assert '"stale"' not in patched
    assert patched.count("reflex-ohif-viewer:cornerstone") == 1


def test_patch_is_skipped_when_the_anchor_is_gone(capsys):
    # A missing anchor means the upstream template changed. That is worth
    # reporting, but not worth failing a build over.
    result = CornerstonePlugin()._patch_config("export default {};\n")
    assert result == "export default {};\n"
    assert "could not patch vite.config.js" in capsys.readouterr().out


def test_dependencies_include_the_browser_events_shim():
    # xmlbuilder2 subclasses Node's EventEmitter; without a real `events`
    # package Vite externalises it to an empty stub and the page dies with
    # "Class extends value undefined is not a constructor or null".
    dependencies = CornerstonePlugin().get_frontend_dependencies()
    assert any(name.startswith("events@") for name in dependencies)
    assert any("@cornerstonejs/core@" in name for name in dependencies)


def test_dependencies_can_be_turned_off():
    assert CornerstonePlugin(declare_dependencies=False).get_frontend_dependencies() == []


def test_wasm_base_path_is_a_root_relative_directory_url():
    assert CornerstonePlugin().wasm_base_path == "/cs-wasm/"
    assert CornerstonePlugin(wasm_dir="/codecs/").wasm_base_path == "/codecs/"


def test_copying_codecs_without_node_modules_is_a_no_op(tmp_path: Path, capsys):
    # The first compile of a fresh app runs before the frontend install.
    assert CornerstonePlugin().copy_codecs(tmp_path) == []


def test_copying_codecs_picks_up_every_codec_package(tmp_path: Path):
    node_modules = tmp_path / ".web" / "node_modules" / "@cornerstonejs"
    for package, filename in (
        ("codec-charls", "charlswasm_decode.wasm"),
        ("codec-openjph", "openjphjs.wasm"),
    ):
        target = node_modules / package / "dist"
        target.mkdir(parents=True)
        (target / filename).write_bytes(b"\x00asm\x01\x00\x00\x00")

    copied = CornerstonePlugin().copy_codecs(tmp_path)
    names = sorted(path.name for path in copied)
    assert names == ["charlswasm_decode.wasm", "openjphjs.wasm"]
    destination = tmp_path / ".web" / "public" / "cs-wasm"
    assert (destination / "openjphjs.wasm").read_bytes().startswith(b"\x00asm")


def test_copying_codecs_twice_is_stable(tmp_path: Path):
    target = tmp_path / ".web" / "node_modules" / "@cornerstonejs" / "codec-charls" / "dist"
    target.mkdir(parents=True)
    (target / "charlswasm_decode.wasm").write_bytes(b"\x00asm\x01\x00\x00\x00")

    plugin = CornerstonePlugin()
    assert plugin.copy_codecs(tmp_path) == plugin.copy_codecs(tmp_path)
