"""Tests for the OHIF ``window.config`` builders."""

import json

import pytest
from reflex_ohif_viewer import (
    PUBLIC_DICOMWEB_ROOT,
    DicomWebDataSource,
    OhifAppConfig,
    docker_run_command,
    public_demo_config,
)


def test_a_config_needs_at_least_one_data_source():
    with pytest.raises(ValueError, match="at least one data source"):
        OhifAppConfig().to_dict()


def test_wado_uri_root_defaults_to_wado_root():
    source = DicomWebDataSource(wado_root="https://p/dicom-web").to_dict()
    assert source["configuration"]["wadoUriRoot"] == "https://p/dicom-web"


def test_default_data_source_name_falls_back_to_the_first_source():
    config = OhifAppConfig(data_sources=[DicomWebDataSource(source_name="pacs")])
    assert config.to_dict()["defaultDataSourceName"] == "pacs"


def test_none_valued_options_are_dropped_so_ohif_uses_its_own_defaults():
    source = DicomWebDataSource(request_options=None, bulk_data_uri=None).to_dict()
    assert "requestOptions" not in source["configuration"]
    assert "bulkDataURI" not in source["configuration"]


def test_extra_keys_are_merged_into_the_source_configuration():
    source = DicomWebDataSource(extra={"customField": 7}).to_dict()
    assert source["configuration"]["customField"] == 7


def test_extra_keys_are_merged_at_the_top_level():
    config = OhifAppConfig(
        data_sources=[DicomWebDataSource()], extra={"oidc": [{"authority": "x"}]}
    )
    assert config.to_dict()["oidc"] == [{"authority": "x"}]


def test_the_public_demo_source_is_configured_for_static_dicomweb():
    # A static DICOMweb bucket cannot answer real QIDO queries, so these three
    # have to be off or OHIF's study list breaks against it.
    configuration = DicomWebDataSource.public_demo().to_dict()["configuration"]
    assert configuration["staticWado"] is True
    assert configuration["qidoSupportsIncludeField"] is False
    assert configuration["supportsFuzzyMatching"] is False
    assert configuration["qidoRoot"] == PUBLIC_DICOMWEB_ROOT


def test_to_json_round_trips():
    config = public_demo_config()
    assert json.loads(config.to_json()) == config.to_dict()


def test_app_config_js_assigns_the_global_ohif_reads():
    text = public_demo_config().to_app_config_js()
    assert text.startswith("window.config = {")
    assert text.rstrip().endswith("};")


def test_docker_command_injects_the_config_and_pins_the_tag():
    command = docker_run_command(public_demo_config(), port=3042)
    assert "-p 3042:80" in command
    assert "-e APP_CONFIG=" in command
    assert "ohif/app:v3.13.8" in command
    assert ":latest" not in command


def test_docker_command_escapes_single_quotes_in_the_config():
    config = OhifAppConfig(data_sources=[DicomWebDataSource(friendly_name="Bob's PACS")])
    command = docker_run_command(config)
    # The whole APP_CONFIG value is single-quoted for the shell, so an embedded
    # quote has to be broken out of and back into.
    assert "'\\''" in command
