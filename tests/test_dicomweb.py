"""Tests for the DICOMweb client's parsing, without touching the network."""

from reflex_ohif_viewer.dicomweb import (
    DicomWebClient,
    SeriesSummary,
    StudySummary,
    naturalize,
)

STUDY_ROW = {
    "0020000D": {"vr": "UI", "Value": ["1.2.3"]},
    "00100010": {"vr": "PN", "Value": [{"Alphabetic": "DOE^JANE"}]},
    "00100020": {"vr": "LO", "Value": ["MRN-1"]},
    "00080020": {"vr": "DA", "Value": ["20260101"]},
    "00081030": {"vr": "LO", "Value": ["CHEST CT"]},
    "00080061": {"vr": "CS", "Value": ["CT"]},
    "00201206": {"vr": "IS", "Value": [3]},
    "00201208": {"vr": "IS", "Value": [412]},
}

SERIES_ROW = {
    "0020000E": {"vr": "UI", "Value": ["4.5.6"]},
    "00080060": {"vr": "CS", "Value": ["CT"]},
    "0008103E": {"vr": "LO", "Value": ["LUNG 1.0"]},
    "00200011": {"vr": "IS", "Value": [2]},
    "00201209": {"vr": "IS", "Value": [135]},
}


def test_person_names_are_flattened_to_their_alphabetic_component():
    assert naturalize(STUDY_ROW)["patient_name"] == "DOE^JANE"


def test_absent_tags_are_omitted_rather_than_returned_empty():
    assert "accession_number" not in naturalize(STUDY_ROW)


def test_study_summary_parses_a_qido_row():
    study = StudySummary.from_dataset(STUDY_ROW)
    assert study.study_instance_uid == "1.2.3"
    assert study.patient_id == "MRN-1"
    assert study.modalities == "CT"
    assert study.number_of_series == 3
    assert study.number_of_instances == 412


def test_study_summary_survives_an_almost_empty_row():
    study = StudySummary.from_dataset({"0020000D": {"vr": "UI", "Value": ["9.9"]}})
    assert study.study_instance_uid == "9.9"
    assert study.patient_name == ""
    assert study.number_of_series == 0


def test_series_summary_parses_a_qido_row():
    series = SeriesSummary.from_dataset(SERIES_ROW, study_instance_uid="1.2.3")
    assert series.study_instance_uid == "1.2.3"
    assert series.series_instance_uid == "4.5.6"
    assert series.modality == "CT"
    assert series.number_of_instances == 135


def test_roots_are_normalised_and_wado_defaults_to_qido():
    client = DicomWebClient("https://p/dicom-web/")
    assert client.qido_root == "https://p/dicom-web"
    assert client.wado_root == "https://p/dicom-web"


def test_custom_headers_are_kept_alongside_the_dicom_json_accept_header():
    client = DicomWebClient("https://p", headers={"Authorization": "Bearer x"})
    assert client.headers["Accept"] == "application/dicom+json"
    assert client.headers["Authorization"] == "Bearer x"
