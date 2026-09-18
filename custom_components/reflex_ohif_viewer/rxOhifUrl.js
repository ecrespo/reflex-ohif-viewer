/**
 * URL construction for an embedded OHIF Viewer v3 build.
 *
 * Kept apart from the React component on purpose: it is pure logic, it is the
 * whole interface to an embedded OHIF viewer, and being plain JavaScript lets
 * the test suite import it under Node and check it against the Python builder
 * in `reflex_ohif_viewer.ohif_viewer.build_ohif_url`. The two must agree.
 *
 * Parameter names and route shapes follow the OHIF v3 source:
 *   - routes: `platform/app/src/routes/buildModeRoutes.tsx`
 *   - params: `platform/app/src/routes/Mode/Mode.tsx`,
 *             `platform/app/src/utils/studyListFilterContract.ts`
 */

/** Query keys OHIF reads case-insensitively on the viewer routes. */
const VIEWER_PARAM_KEYS = {
  initialSeriesInstanceUid: "initialSeriesInstanceUID",
  initialSopInstanceUid: "initialSopInstanceUID",
  hangingProtocolId: "hangingProtocolId",
  stageId: "stageId",
  token: "token",
  customization: "customization",
  theme: "theme",
  useNextViewports: "useNextViewports",
  viewportRendering: "viewportRendering",
  multimonitor: "multimonitor",
  screenNumber: "screenNumber",
};

/** Query keys the OHIF study list (WorkList) understands. */
const WORKLIST_PARAM_KEYS = [
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
];

/**
 * Normalise a value that may arrive as a string, a list, or null.
 *
 * @param {unknown} value A scalar or list of scalars.
 * @returns {string[]} Non-empty string values.
 */
function toList(value) {
  if (value === null || value === undefined || value === "") {
    return [];
  }
  const list = Array.isArray(value) ? value : [value];
  return list.map((item) => String(item).trim()).filter(Boolean);
}

/**
 * Build the full OHIF URL for the given props.
 *
 * Mirrors `build_ohif_url()` on the Python side; both must stay in step.
 *
 * @param {object} props The component props.
 * @returns {string} An absolute or root-relative URL, or "" when unusable.
 */
export function buildOhifUrl(props) {
  const {
    baseUrl = "",
    mode = "viewer",
    dataSource = "",
    studyList = false,
    studyInstanceUids,
    seriesInstanceUids,
    configUrl = "",
    debug = false,
    extraParams = null,
    worklistFilters = null,
  } = props;

  if (!baseUrl) {
    return "";
  }

  const trimmedBase = baseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams();

  if (studyList) {
    const filters = worklistFilters || {};
    for (const key of WORKLIST_PARAM_KEYS) {
      const value = filters[key] ?? props[key];
      if (value !== undefined && value !== null && value !== "") {
        params.set(key, String(value));
      }
    }
    if (dataSource) {
      params.set("dataSources", dataSource);
    }
  } else {
    for (const uid of toList(studyInstanceUids)) {
      params.append("StudyInstanceUIDs", uid);
    }
    const series = toList(seriesInstanceUids);
    if (series.length) {
      params.set("SeriesInstanceUIDs", series.join(","));
    }
    for (const [prop, key] of Object.entries(VIEWER_PARAM_KEYS)) {
      const value = props[prop];
      if (value !== undefined && value !== null && value !== "" && value !== false) {
        params.set(key, value === true ? "true" : String(value));
      }
    }
  }

  if (configUrl) {
    // `configUrl` is read case-sensitively from `window.location.search`.
    params.set("configUrl", configUrl);
  }
  if (debug) {
    params.set("debug", "true");
  }
  for (const [key, value] of Object.entries(extraParams || {})) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }

  const path = studyList ? "" : dataSource ? `${mode}/${dataSource}` : mode;
  const query = params.toString();
  const url = path ? `${trimmedBase}/${path}` : `${trimmedBase}/`;
  return query ? `${url}?${query}` : url;
}
