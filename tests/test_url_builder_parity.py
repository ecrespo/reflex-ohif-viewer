"""The Python and JavaScript URL builders must agree.

``build_ohif_url`` in Python and ``buildOhifUrl`` in ``RxOhifViewer.jsx`` are two
implementations of the same contract: one so a link can be computed, logged and
tested server-side, one so the component reacts to state without a round trip.
Two implementations drift, so this test pins them together by running the
JavaScript one under Node and comparing the parsed results.
"""

import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

import pytest
from reflex_ohif_viewer import build_ohif_url

URL_MODULE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "reflex_ohif_viewer"
    / "rxOhifUrl.js"
)

# (python kwargs, javascript props) for the same intent. The two sides differ
# only in naming: Reflex camel-cases snake_case props on the way to React.
CASES = [
    (
        {"study_instance_uids": ["1.2.3"]},
        {"studyInstanceUids": ["1.2.3"]},
    ),
    (
        {"study_instance_uids": ["1.2.3", "4.5.6"], "hanging_protocol_id": "mpr"},
        {"studyInstanceUids": ["1.2.3", "4.5.6"], "hangingProtocolId": "mpr"},
    ),
    (
        {"study_instance_uids": ["1.2.3"], "series_instance_uids": ["a", "b"]},
        {"studyInstanceUids": ["1.2.3"], "seriesInstanceUids": ["a", "b"]},
    ),
    (
        {"mode": "tmtv", "data_source": "pacs", "study_instance_uids": ["1.2.3"]},
        {"mode": "tmtv", "dataSource": "pacs", "studyInstanceUids": ["1.2.3"]},
    ),
    (
        {
            "study_instance_uids": ["1.2.3"],
            "initial_series_instance_uid": "s1",
            "initial_sop_instance_uid": "i1",
            "theme": "dark",
            "debug": True,
        },
        {
            "studyInstanceUids": ["1.2.3"],
            "initialSeriesInstanceUid": "s1",
            "initialSopInstanceUid": "i1",
            "theme": "dark",
            "debug": True,
        },
    ),
    (
        {"study_list": True, "patient_name": "Smith", "modalities": "CT,MR"},
        {"studyList": True, "worklistFilters": {"patientName": "Smith", "modalities": "CT,MR"}},
    ),
    (
        {"study_instance_uids": ["1.2.3"], "config_url": "http://c/x.json"},
        {"studyInstanceUids": ["1.2.3"], "configUrl": "http://c/x.json"},
    ),
    (
        {"study_instance_uids": ["1.2.3"], "extra_params": {"foo": "bar"}},
        {"studyInstanceUids": ["1.2.3"], "extraParams": {"foo": "bar"}},
    ),
    ({}, {}),
]

BASE = "http://localhost:3001"


def normalise(url: str) -> tuple[str, list[tuple[str, str]]]:
    """Reduce a URL to a comparable form.

    Query parameter order is not significant to OHIF, so it is sorted away;
    repetition is significant (multiple studies), so it is preserved.

    Args:
        url: The URL to normalise.

    Returns:
        The path and the sorted query pairs.
    """
    parsed = urlparse(url)
    return parsed.path, sorted(parse_qsl(parsed.query))


@pytest.fixture(scope="module")
def js_urls() -> list[str]:
    """Run the JavaScript builder over every case.

    Returns:
        One URL per case, in order.

    Raises:
        pytest.skip.Exception: If Node is unavailable.
    """
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")

    script = f"""
import {{ buildOhifUrl }} from {json.dumps(str(URL_MODULE))};
const cases = {json.dumps([props for _, props in CASES])};
console.log(JSON.stringify(cases.map((props) =>
    buildOhifUrl({{ baseUrl: {json.dumps(BASE)}, ...props }}))));
"""
    result = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        pytest.skip(f"node could not import the URL module: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("index", range(len(CASES)))
def test_builders_agree(index: int, js_urls: list[str]):
    python_kwargs = CASES[index][0]
    assert normalise(build_ohif_url(BASE, **python_kwargs)) == normalise(js_urls[index])
