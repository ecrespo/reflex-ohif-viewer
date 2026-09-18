"""Tests for the OHIF URL builder.

The URL is the entire interface to an embedded OHIF viewer, so its shape is
worth pinning down. Parameter names and casing here match the OHIF 3.13 source:
``StudyInstanceUIDs`` is repeated rather than comma-joined, ``SeriesInstanceUIDs``
is comma-joined, and ``configUrl`` is read case-sensitively.
"""

from urllib.parse import parse_qs, urlparse

import pytest
from reflex_ohif_viewer import build_ohif_url


def query(url: str) -> dict[str, list[str]]:
    """Parse the query string of a URL.

    Args:
        url: The URL to parse.

    Returns:
        The parsed query parameters.
    """
    return parse_qs(urlparse(url).query)


def test_empty_base_url_returns_empty_string():
    assert build_ohif_url("") == ""


def test_default_mode_is_viewer():
    url = build_ohif_url("http://h", study_instance_uids=["1.2.3"])
    assert urlparse(url).path == "/viewer"


def test_trailing_slash_on_base_url_is_not_doubled():
    url = build_ohif_url("http://h/ohif/", study_instance_uids=["1.2.3"])
    assert urlparse(url).path == "/ohif/viewer"


def test_data_source_becomes_a_path_segment():
    url = build_ohif_url("http://h", data_source="pacs", study_instance_uids=["1.2.3"])
    assert urlparse(url).path == "/viewer/pacs"


def test_multiple_studies_repeat_the_parameter():
    # OHIF concatenates getAll('StudyInstanceUIDs'), which is how a current
    # study plus priors is expressed.
    url = build_ohif_url("http://h", study_instance_uids=["1.2.3", "4.5.6"])
    assert query(url)["StudyInstanceUIDs"] == ["1.2.3", "4.5.6"]


def test_a_single_study_may_be_passed_as_a_string():
    url = build_ohif_url("http://h", study_instance_uids="1.2.3")
    assert query(url)["StudyInstanceUIDs"] == ["1.2.3"]


def test_series_are_comma_joined_into_one_parameter():
    url = build_ohif_url("http://h", study_instance_uids=["1.2.3"], series_instance_uids=["a", "b"])
    assert query(url)["SeriesInstanceUIDs"] == ["a,b"]


def test_blank_and_whitespace_only_uids_are_dropped():
    url = build_ohif_url("http://h", study_instance_uids=["1.2.3", "", "   "])
    assert query(url)["StudyInstanceUIDs"] == ["1.2.3"]


@pytest.mark.parametrize(
    ("kwarg", "expected_key", "value"),
    [
        ("hanging_protocol_id", "hangingProtocolId", "mpr"),
        ("stage_id", "stageId", "stage-2"),
        ("token", "token", "abc"),
        ("initial_series_instance_uid", "initialSeriesInstanceUID", "s1"),
        ("initial_sop_instance_uid", "initialSopInstanceUID", "i1"),
        ("theme", "theme", "dark"),
        ("customization", "customization", "site-a"),
        ("viewport_rendering", "viewportRendering", "cpu"),
    ],
)
def test_viewer_parameters_use_ohif_casing(kwarg, expected_key, value):
    url = build_ohif_url("http://h", study_instance_uids=["1.2.3"], **{kwarg: value})
    assert query(url)[expected_key] == [value]


def test_falsey_viewer_parameters_are_omitted():
    url = build_ohif_url(
        "http://h",
        study_instance_uids=["1.2.3"],
        hanging_protocol_id="",
        token=None,
        use_next_viewports=False,
    )
    keys = set(query(url))
    assert keys == {"StudyInstanceUIDs"}


def test_true_becomes_the_string_true():
    url = build_ohif_url("http://h", study_instance_uids=["1"], use_next_viewports=True)
    assert query(url)["useNextViewports"] == ["true"]


def test_config_url_keeps_its_camel_case():
    # loadDynamicConfig reads query.get('configUrl') without lowercasing.
    url = build_ohif_url("http://h", study_instance_uids=["1"], config_url="http://c/x.json")
    assert "configUrl=" in url


def test_debug_flag():
    assert "debug=true" in build_ohif_url("http://h", study_instance_uids=["1"], debug=True)


def test_extra_params_are_merged():
    url = build_ohif_url("http://h", study_instance_uids=["1"], extra_params={"foo": "bar"})
    assert query(url)["foo"] == ["bar"]


def test_study_list_uses_the_root_route():
    url = build_ohif_url("http://h", study_list=True, patient_name="Smith")
    assert urlparse(url).path == "/"
    assert query(url)["patientName"] == ["Smith"]


def test_study_list_accepts_every_worklist_key():
    url = build_ohif_url(
        "http://h",
        study_list=True,
        patient_name="Smith",
        mrn="123",
        description="chest",
        accession="A1",
        modalities="CT,MR",
        start_date="20260101",
        end_date="20261231",
        sort_by="studyDate",
        sort_direction="desc",
        page_number=2,
        results_per_page=25,
    )
    keys = set(query(url))
    assert keys == {
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
    }


def test_study_list_puts_the_data_source_in_the_query_not_the_path():
    url = build_ohif_url("http://h", study_list=True, data_source="pacs")
    assert urlparse(url).path == "/"
    assert query(url)["dataSources"] == ["pacs"]


def test_no_query_means_no_question_mark():
    assert build_ohif_url("http://h", study_list=True) == "http://h/"
