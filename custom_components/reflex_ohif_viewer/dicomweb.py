"""A small, dependency-light DICOMweb (QIDO-RS / WADO-RS) client.

The native viewport talks DICOMweb from the browser, but a Reflex app usually
also wants to *list* studies and series server-side — to build a study browser,
to validate a UID before handing it to the viewer, or to drive a series picker
from Python state. That is what this client is for.

It uses ``httpx``, which Reflex already depends on, and returns plain
dictionaries rather than DICOM-JSON so the results drop straight into
``rx.State`` fields.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import httpx

from .constants import PUBLIC_DICOMWEB_ROOT

__all__ = [
    "DicomWebClient",
    "DicomWebError",
    "SeriesSummary",
    "StudySummary",
    "naturalize",
]

# DICOM tag keywords used by QIDO-RS responses, as hexadecimal group+element.
_TAGS = {
    "study_instance_uid": "0020000D",
    "series_instance_uid": "0020000E",
    "sop_instance_uid": "00080018",
    "patient_name": "00100010",
    "patient_id": "00100020",
    "patient_birth_date": "00100030",
    "patient_sex": "00100040",
    "study_date": "00080020",
    "study_time": "00080030",
    "study_description": "00081030",
    "accession_number": "00080050",
    "referring_physician": "00080090",
    "modality": "00080060",
    "modalities_in_study": "00080061",
    "series_description": "0008103E",
    "series_number": "00200011",
    "instance_number": "00200013",
    "number_of_series": "00201206",
    "number_of_instances": "00201208",
    "number_of_series_instances": "00201209",
    "institution_name": "00080080",
    "manufacturer": "00080070",
    "body_part_examined": "00180015",
    "rows": "00280010",
    "columns": "00280011",
}


class DicomWebError(RuntimeError):
    """Raised when a DICOMweb request fails or returns something unusable."""


def _value(dataset: dict[str, Any], tag: str) -> str:
    """Extract the first value of ``tag`` from a DICOM-JSON dataset.

    Person-name values arrive as ``{"Alphabetic": "..."}`` and are flattened.

    Args:
        dataset: A DICOM-JSON object.
        tag: The 8-character hexadecimal tag.

    Returns:
        The value as a string, or an empty string when absent.

    """
    values = dataset.get(tag, {}).get("Value")
    if not values:
        return ""
    first = values[0]
    if isinstance(first, dict):
        return str(first.get("Alphabetic", ""))
    return str(first)


def naturalize(dataset: dict[str, Any]) -> dict[str, str]:
    """Convert a DICOM-JSON dataset into a flat mapping of readable names.

    Args:
        dataset: A DICOM-JSON object from a QIDO-RS response.

    Returns:
        A mapping of snake_case keyword to string value, omitting absent tags.

    """
    out: dict[str, str] = {}
    for name, tag in _TAGS.items():
        value = _value(dataset, tag)
        if value:
            out[name] = value
    return out


@dataclasses.dataclass
class StudySummary:
    """One row of a QIDO-RS study search.

    Attributes:
        study_instance_uid: The study UID.
        patient_name: Patient name, alphabetic component.
        patient_id: Patient identifier (MRN).
        study_date: Study date as ``YYYYMMDD``.
        study_description: Free-text study description.
        accession_number: Accession number.
        modalities: Modalities present in the study.
        number_of_series: Series count, when the server reports it.
        number_of_instances: Instance count, when the server reports it.
        raw: The naturalized mapping, for fields not promoted to attributes.

    """

    study_instance_uid: str
    patient_name: str = ""
    patient_id: str = ""
    study_date: str = ""
    study_description: str = ""
    accession_number: str = ""
    modalities: str = ""
    number_of_series: int = 0
    number_of_instances: int = 0
    raw: dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dataset(cls, dataset: dict[str, Any]) -> StudySummary:
        """Build a summary from a DICOM-JSON study dataset.

        Args:
            dataset: A QIDO-RS study result.

        Returns:
            The parsed summary.

        """
        flat = naturalize(dataset)
        return cls(
            study_instance_uid=flat.get("study_instance_uid", ""),
            patient_name=flat.get("patient_name", ""),
            patient_id=flat.get("patient_id", ""),
            study_date=flat.get("study_date", ""),
            study_description=flat.get("study_description", ""),
            accession_number=flat.get("accession_number", ""),
            modalities=flat.get("modalities_in_study", flat.get("modality", "")),
            number_of_series=int(flat.get("number_of_series", 0) or 0),
            number_of_instances=int(flat.get("number_of_instances", 0) or 0),
            raw=flat,
        )


@dataclasses.dataclass
class SeriesSummary:
    """One row of a QIDO-RS series search.

    Attributes:
        study_instance_uid: The parent study UID.
        series_instance_uid: The series UID.
        series_description: Free-text series description.
        series_number: Series number as reported by the modality.
        modality: The series modality, e.g. ``CT`` or ``PT``.
        number_of_instances: Instance count, when the server reports it.
        body_part_examined: Body part, when present.
        raw: The naturalized mapping.

    """

    study_instance_uid: str
    series_instance_uid: str
    series_description: str = ""
    series_number: str = ""
    modality: str = ""
    number_of_instances: int = 0
    body_part_examined: str = ""
    raw: dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def from_dataset(cls, dataset: dict[str, Any], study_instance_uid: str = "") -> SeriesSummary:
        """Build a summary from a DICOM-JSON series dataset.

        Args:
            dataset: A QIDO-RS series result.
            study_instance_uid: Fallback study UID when the row omits it.

        Returns:
            The parsed summary.

        """
        flat = naturalize(dataset)
        return cls(
            study_instance_uid=flat.get("study_instance_uid", study_instance_uid),
            series_instance_uid=flat.get("series_instance_uid", ""),
            series_description=flat.get("series_description", ""),
            series_number=flat.get("series_number", ""),
            modality=flat.get("modality", ""),
            number_of_instances=int(
                flat.get("number_of_series_instances", flat.get("number_of_instances", 0)) or 0
            ),
            body_part_examined=flat.get("body_part_examined", ""),
            raw=flat,
        )


class DicomWebClient:
    """A minimal QIDO-RS / WADO-RS client for driving a Reflex study browser.

    Only the read paths a viewer needs are implemented: study search, series
    search, instance search and series metadata. Everything returns plain
    Python values.

    Example:
        ```python
        client = DicomWebClient()
        studies = client.search_studies(limit=20)
        series = client.search_series(studies[0].study_instance_uid)
        ```

    """

    def __init__(
        self,
        qido_root: str = PUBLIC_DICOMWEB_ROOT,
        wado_root: str | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        verify: bool = True,
    ) -> None:
        """Initialise the client.

        Args:
            qido_root: QIDO-RS root URL, without a trailing slash.
            wado_root: WADO-RS root URL. Defaults to ``qido_root``.
            headers: Extra request headers, typically ``Authorization``.
            timeout: Per-request timeout in seconds.
            verify: Whether to verify TLS certificates. Only turn this off for
                a PACS on a trusted network with a self-signed certificate.

        """
        self.qido_root = qido_root.rstrip("/")
        self.wado_root = (wado_root or qido_root).rstrip("/")
        self.headers = {"Accept": "application/dicom+json", **(headers or {})}
        self.timeout = timeout
        self.verify = verify

    def _get(self, url: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Perform a QIDO-RS GET and return the DICOM-JSON array.

        Args:
            url: The absolute URL to request.
            params: Query parameters.

        Returns:
            The decoded list of datasets, empty when the server returns 204.

        Raises:
            DicomWebError: If the request fails or the body is not DICOM-JSON.

        """
        try:
            response = httpx.get(
                url,
                params=params,
                headers=self.headers,
                timeout=self.timeout,
                verify=self.verify,
                follow_redirects=True,
            )
        except httpx.HTTPError as exc:  # pragma: no cover - network dependent
            msg = f"DICOMweb request to {url} failed: {exc}"
            raise DicomWebError(msg) from exc

        if response.status_code == 204:
            return []
        if response.status_code >= 400:
            msg = (
                f"DICOMweb request to {url} returned HTTP {response.status_code}: "
                f"{response.text[:200]}"
            )
            raise DicomWebError(msg)
        try:
            payload = response.json()
        except ValueError as exc:
            msg = f"DICOMweb response from {url} was not JSON."
            raise DicomWebError(msg) from exc
        if not isinstance(payload, list):
            msg = f"DICOMweb response from {url} was not a DICOM-JSON array."
            raise DicomWebError(msg)
        return payload

    def search_studies(
        self,
        patient_name: str = "",
        patient_id: str = "",
        accession_number: str = "",
        study_date: str = "",
        modalities_in_study: str = "",
        study_description: str = "",
        limit: int = 50,
        offset: int = 0,
        extra_params: dict[str, Any] | None = None,
    ) -> list[StudySummary]:
        """Search studies with QIDO-RS.

        Args:
            patient_name: ``PatientName`` filter. Wildcards depend on server.
            patient_id: ``PatientID`` filter.
            accession_number: ``AccessionNumber`` filter.
            study_date: ``StudyDate`` filter, ``YYYYMMDD`` or a range.
            modalities_in_study: ``ModalitiesInStudy`` filter, e.g. ``CT``.
            study_description: ``StudyDescription`` filter.
            limit: Maximum rows to return.
            offset: Rows to skip.
            extra_params: Any further QIDO parameters, merged last.

        Returns:
            The matching studies.

        """
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        filters = {
            "PatientName": patient_name,
            "PatientID": patient_id,
            "AccessionNumber": accession_number,
            "StudyDate": study_date,
            "ModalitiesInStudy": modalities_in_study,
            "StudyDescription": study_description,
        }
        params.update({key: value for key, value in filters.items() if value})
        params.update(extra_params or {})
        datasets = self._get(f"{self.qido_root}/studies", params)
        return [StudySummary.from_dataset(dataset) for dataset in datasets]

    def search_series(
        self,
        study_instance_uid: str,
        modality: str = "",
        limit: int = 200,
        extra_params: dict[str, Any] | None = None,
    ) -> list[SeriesSummary]:
        """List the series of a study with QIDO-RS.

        Args:
            study_instance_uid: The study to list.
            modality: Optional ``Modality`` filter.
            limit: Maximum rows to return.
            extra_params: Any further QIDO parameters, merged last.

        Returns:
            The series of the study, sorted by series number when available.

        """
        params: dict[str, Any] = {"limit": limit}
        if modality:
            params["Modality"] = modality
        params.update(extra_params or {})
        datasets = self._get(f"{self.qido_root}/studies/{study_instance_uid}/series", params)
        series = [SeriesSummary.from_dataset(dataset, study_instance_uid) for dataset in datasets]

        def sort_key(item: SeriesSummary) -> tuple[int, str]:
            """Sort by numeric series number, falling back to description.

            Args:
                item: The series to key.

            Returns:
                A sortable tuple.

            """
            try:
                return (int(item.series_number), item.series_description)
            except (TypeError, ValueError):
                return (10**9, item.series_description)

        return sorted(series, key=sort_key)

    def search_instances(
        self,
        study_instance_uid: str,
        series_instance_uid: str,
        limit: int = 2000,
    ) -> list[dict[str, str]]:
        """List the instances of a series with QIDO-RS.

        Args:
            study_instance_uid: The parent study.
            series_instance_uid: The series to list.
            limit: Maximum rows to return.

        Returns:
            Naturalized instance mappings, sorted by instance number.

        """
        datasets = self._get(
            f"{self.qido_root}/studies/{study_instance_uid}/series/{series_instance_uid}/instances",
            {"limit": limit},
        )
        instances = [naturalize(dataset) for dataset in datasets]

        def sort_key(item: dict[str, str]) -> int:
            """Sort instances by ``InstanceNumber``.

            Args:
                item: The naturalized instance.

            Returns:
                The instance number, or a large value when absent.

            """
            try:
                return int(item.get("instance_number", 10**9))
            except (TypeError, ValueError):
                return 10**9

        return sorted(instances, key=sort_key)

    def series_metadata(
        self, study_instance_uid: str, series_instance_uid: str
    ) -> list[dict[str, Any]]:
        """Fetch full WADO-RS metadata for a series.

        Args:
            study_instance_uid: The parent study.
            series_instance_uid: The series to fetch.

        Returns:
            The raw DICOM-JSON instances.

        """
        return self._get(
            f"{self.wado_root}/studies/{study_instance_uid}/series/{series_instance_uid}/metadata"
        )

    def image_ids(self, study_instance_uid: str, series_instance_uid: str) -> list[str]:
        """Build the Cornerstone ``wadors:`` imageIds for a series.

        Useful when you want Python to decide exactly which frames the viewport
        shows. Pass the result to the ``image_ids`` prop of ``dicom_viewer``.

        Note that the browser still fetches the metadata itself; this call is a
        convenience for slicing, filtering or reordering a series server-side.

        Args:
            study_instance_uid: The parent study.
            series_instance_uid: The series to enumerate.

        Returns:
            One imageId per frame, in instance-number order.

        """
        instances = self.series_metadata(study_instance_uid, series_instance_uid)

        def instance_number(dataset: dict[str, Any]) -> int:
            """Read ``InstanceNumber`` from a dataset.

            Args:
                dataset: The DICOM-JSON instance.

            Returns:
                The instance number, or a large value when absent.

            """
            try:
                return int(_value(dataset, _TAGS["instance_number"]) or 10**9)
            except ValueError:
                return 10**9

        image_ids: list[str] = []
        for dataset in sorted(instances, key=instance_number):
            sop_uid = _value(dataset, _TAGS["sop_instance_uid"])
            series_uid = _value(dataset, _TAGS["series_instance_uid"]) or series_instance_uid
            if not sop_uid:
                continue
            frames = _value(dataset, "00280008")
            try:
                frame_count = max(1, int(frames or 1))
            except ValueError:
                frame_count = 1
            base = (
                f"wadors:{self.wado_root}/studies/{study_instance_uid}"
                f"/series/{series_uid}/instances/{sop_uid}/frames/"
            )
            image_ids.extend(f"{base}{frame}" for frame in range(1, frame_count + 1))
        return image_ids
