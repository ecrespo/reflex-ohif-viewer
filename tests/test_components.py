"""Tests for component construction and the imperative API helpers."""

import pytest
import reflex as rx
from reflex_ohif_viewer import (
    ALL_TOOLS,
    ANNOTATION_TOOLS,
    DEFAULT_TOOLS,
    DEMO_STUDIES,
    NAVIGATION_TOOLS,
    OVERLAY_TOOLS,
    SEGMENTATION_TOOLS,
    WINDOW_PRESETS,
    DicomViewer,
    OhifViewer,
    dicom_viewer,
    jump_to_slice,
    ohif_viewer,
    set_tool,
    set_window_preset,
    viewer_call,
    window_preset_range,
)


def script_of(spec: rx.event.EventSpec) -> str:
    """Return the JavaScript `rx.call_script` was handed.

    `str(spec)` is a repr of the whole event spec and gets truncated, so the
    script is read off the `javascript_code` argument instead.
    """
    for name, value in spec.args:
        if str(name) == "javascript_code":
            return value._var_value
    raise AssertionError(f"{spec!r} is not a call_script spec")


def test_dicom_viewer_is_client_only():
    # Cornerstone touches window, document and Worker at import time, so the
    # component must never be server-rendered.
    from reflex.components.component import NoSSRComponent

    assert issubclass(DicomViewer, NoSSRComponent)


def test_dicom_viewer_builds():
    component = dicom_viewer(
        wado_rs_root="https://p/dicom-web",
        study_instance_uid="1.2.3",
        series_instance_uid="4.5.6",
        viewport_id="vp",
    )
    assert isinstance(component, DicomViewer)
    assert component.library is not None
    assert component.library.startswith("$/public/")


def test_dicom_viewer_declares_the_cornerstone_packages():
    component = dicom_viewer()
    joined = " ".join(component.lib_dependencies)
    for package in ("core", "tools", "dicom-image-loader", "metadata", "utils"):
        assert f"@cornerstonejs/{package}@" in joined
    assert "dicom-parser@" in joined
    assert "dicomweb-client@" in joined


def test_an_unknown_tool_is_rejected_at_build_time():
    # A console warning at runtime is far too easy to miss.
    with pytest.raises(ValueError, match="Unknown Cornerstone tool"):
        dicom_viewer(tools=["WindowLevel", "Lenght"])


def test_an_unknown_active_tool_is_rejected_at_build_time():
    with pytest.raises(ValueError, match="Unknown active_tool"):
        dicom_viewer(active_tool="Measure")


def test_every_default_tool_is_a_known_tool():
    assert set(DEFAULT_TOOLS) <= set(ALL_TOOLS)


def test_the_tool_groups_partition_all_tools():
    grouped = NAVIGATION_TOOLS + ANNOTATION_TOOLS + OVERLAY_TOOLS + SEGMENTATION_TOOLS
    assert sorted(grouped) == sorted(ALL_TOOLS)
    assert len(set(grouped)) == len(grouped)


def test_ohif_viewer_builds():
    component = ohif_viewer(base_url="http://localhost:3001")
    assert isinstance(component, OhifViewer)
    assert component.library.startswith("$/public/")


def test_ohif_viewer_is_server_rendered():
    # An iframe is safe to prerender, and doing so keeps the layout stable.
    from reflex.components.component import NoSSRComponent

    assert not issubclass(OhifViewer, NoSSRComponent)


def test_imperative_helpers_return_event_specs():
    for spec in (
        set_tool("vp", "Length"),
        jump_to_slice("vp", 3),
        set_window_preset("vp", "CT Lung"),
    ):
        assert isinstance(spec, rx.event.EventSpec)


def test_imperative_helpers_target_the_named_viewport():
    script = script_of(set_tool("my-viewport", "Length"))
    assert "__rxDicomViewers" in script
    assert "my-viewport" in script
    assert "setTool" in script


def test_viewer_call_json_encodes_the_viewport_id_and_arguments():
    script = script_of(viewer_call('vp"; alert(1); //', "jumpToSlice", 'x"); alert(2); //'))
    # Both are JSON string literals, so neither can break out of its quotes:
    # the closing quote of the payload arrives escaped, never bare.
    assert 'vp\\"; alert(1)' in script
    assert 'x\\"); alert(2)' in script
    assert 'vp"; alert(1)' not in script
    assert 'x"); alert(2)' not in script


def test_viewer_call_rejects_a_method_name_that_is_not_an_identifier():
    # The method is a property access and cannot be JSON-encoded, so it is the
    # one part of the generated script that has to be validated instead.
    for method in ("jumpToSlice(0); alert(1); //", "", "toString()", "a-b", "a.b"):
        with pytest.raises(ValueError, match="JavaScript identifier"):
            viewer_call("vp", method)


def test_viewer_call_accepts_the_identifiers_the_runtime_registers():
    for method in ("jumpToSlice", "setTool", "_private", "$dollar", "a1"):
        assert isinstance(viewer_call("vp", method), rx.event.EventSpec)


def test_ohif_viewer_exposes_every_parameter_the_url_builder_emits():
    # A prop the builder knows about but the component does not declare is
    # unreachable: Reflex only forwards declared props to the frontend.
    from reflex_ohif_viewer.ohif_viewer import _VIEWER_PARAMS

    declared = set(OhifViewer.get_props())
    assert set(_VIEWER_PARAMS) <= declared


def test_window_preset_lookup():
    assert window_preset_range("CT Lung") == (1500, -600)


def test_unknown_window_preset_raises():
    with pytest.raises(KeyError, match="Unknown window preset"):
        window_preset_range("CT Spleen")


def test_window_presets_are_plausible():
    for name, (width, center) in WINDOW_PRESETS.items():
        assert width > 0, f"{name} has a non-positive window width"
        assert -1000 < center < 1000, f"{name} has an implausible window center"


def test_demo_studies_carry_real_looking_uids():
    for slug, study in DEMO_STUDIES.items():
        assert study.study_instance_uid.count(".") > 3, slug
        for label, uid in study.series.items():
            assert uid.count(".") > 3, f"{slug}/{label}"
