/**
 * Shared Cornerstone3D runtime helpers for the Reflex `reflex-ohif-viewer`
 * custom component.
 *
 * Everything in this module is loaded lazily through dynamic `import()` so that
 * no Cornerstone code executes during server-side rendering / prerendering.
 * Cornerstone touches `window`, `document`, `navigator` and `Worker` at module
 * evaluation time, so a static import would break the Reflex production build.
 */

/** @type {Promise<object> | null} */
let initPromise = null;

/** Auth headers registered per DICOMweb root, consumed by `beforeSend`. */
const headerRegistry = [];

/** Registry of live viewer instances, keyed by viewport id (imperative API). */
const viewerRegistry = {};

if (typeof window !== "undefined") {
  window.__rxDicomViewers = viewerRegistry;
}

/**
 * Register Authorization / custom headers for every request whose imageId or
 * URL starts with `root`. Later registrations for the same root win.
 *
 * @param {string} root DICOMweb root URL (`wadoRsRoot`).
 * @param {Record<string, string>} headers Headers to attach.
 */
export function registerHeaders(root, headers) {
  if (!root || !headers || Object.keys(headers).length === 0) {
    return;
  }
  const existing = headerRegistry.find((entry) => entry.root === root);
  if (existing) {
    existing.headers = headers;
  } else {
    headerRegistry.push({ root, headers });
  }
}

/**
 * Look up the headers registered for a given imageId / URL.
 *
 * @param {string} target An imageId or plain URL.
 * @returns {Record<string, string>} The matching headers, or an empty object.
 */
function headersFor(target) {
  if (!target) {
    return {};
  }
  const url = String(target).replace(/^wadors:/, "").replace(/^wadouri:/, "");
  let best = null;
  for (const entry of headerRegistry) {
    if (url.startsWith(entry.root) && (!best || entry.root.length > best.root.length)) {
      best = entry;
    }
  }
  return best ? best.headers : {};
}

/**
 * The exact list of tool classes this component knows how to register.
 * Keys are the public `toolName` strings exposed through the Python API.
 */
const TOOL_CLASS_NAMES = {
  Pan: "PanTool",
  Zoom: "ZoomTool",
  WindowLevel: "WindowLevelTool",
  WindowLevelRegion: "WindowLevelRegionTool",
  StackScroll: "StackScrollTool",
  PlanarRotate: "PlanarRotateTool",
  TrackballRotate: "TrackballRotateTool",
  VolumeRotateMouseWheel: "VolumeRotateTool",
  Magnify: "MagnifyTool",
  AdvancedMagnify: "AdvancedMagnifyTool",
  DragProbe: "DragProbeTool",
  Length: "LengthTool",
  Height: "HeightTool",
  Probe: "ProbeTool",
  RectangleROI: "RectangleROITool",
  EllipticalROI: "EllipticalROITool",
  CircleROI: "CircleROITool",
  Bidirectional: "BidirectionalTool",
  Angle: "AngleTool",
  CobbAngle: "CobbAngleTool",
  ArrowAnnotate: "ArrowAnnotateTool",
  PlanarFreehandROI: "PlanarFreehandROITool",
  SplineROI: "SplineROITool",
  LivewireContour: "LivewireContourTool",
  KeyImage: "KeyImageTool",
  Label: "LabelTool",
  Eraser: "EraserTool",
  Crosshairs: "CrosshairsTool",
  ReferenceLines: "ReferenceLinesTool",
  ScaleOverlay: "ScaleOverlayTool",
  OrientationMarker: "OrientationMarkerTool",
  Brush: "BrushTool",
  RectangleScissor: "RectangleScissorsTool",
  CircleScissor: "CircleScissorsTool",
  SphereScissor: "SphereScissorsTool",
  PaintFill: "PaintFillTool",
  SegmentSelect: "SegmentSelectTool",
};

/**
 * Initialise Cornerstone3D exactly once per page and return the loaded modules.
 *
 * @param {object} options Initialisation options.
 * @param {number} [options.maxWebWorkers] Worker pool size for frame decoding.
 * @param {string} [options.wasmBasePath] Directory serving the codec `.wasm`
 *   files. Set this when the bundler fails to resolve them (the classic
 *   `expected magic word 00 61 73 6d, found 3c 21 64 6f` error).
 * @returns {Promise<{core: object, tools: object, loader: object}>}
 */
export function ensureCornerstone(options = {}) {
  if (initPromise) {
    return initPromise;
  }
  initPromise = (async () => {
    const [core, tools, loaderModule] = await Promise.all([
      import("@cornerstonejs/core"),
      import("@cornerstonejs/tools"),
      import("@cornerstonejs/dicom-image-loader"),
    ]);

    const loader = loaderModule.default ?? loaderModule;

    core.init();

    const loaderOptions = {
      maxWebWorkers: Math.max(
        1,
        options.maxWebWorkers ||
          Math.floor((globalThis.navigator?.hardwareConcurrency || 2) / 2)
      ),
      beforeSend: (_xhr, imageId, defaultHeaders) => ({
        ...defaultHeaders,
        ...headersFor(imageId),
      }),
    };
    if (options.wasmBasePath) {
      loaderOptions.wasmBasePath = options.wasmBasePath;
    }
    (loaderModule.init ?? loader.init)(loaderOptions);

    tools.init();

    // Register every known tool class with the global registry. `addTool` is
    // idempotent per class but we only ever run this block once anyway.
    for (const className of new Set(Object.values(TOOL_CLASS_NAMES))) {
      const ToolClass = tools[className];
      if (ToolClass) {
        try {
          tools.addTool(ToolClass);
        } catch {
          /* already registered */
        }
      }
    }

    return { core, tools, loader };
  })();
  return initPromise;
}

/**
 * Translate a public tool name into the Cornerstone `toolName` string.
 *
 * Reading `ToolClass.toolName` rather than hard-coding the literal keeps the
 * component working under minifiers that mangle class names.
 *
 * @param {object} tools The `@cornerstonejs/tools` module.
 * @param {string} name The public tool name.
 * @returns {string | null} The resolved Cornerstone tool name.
 */
export function resolveToolName(tools, name) {
  const className = TOOL_CLASS_NAMES[name];
  if (className && tools[className]?.toolName) {
    return tools[className].toolName;
  }
  return className ? null : name;
}

/** Public tool names this component can register. */
export const SUPPORTED_TOOLS = Object.keys(TOOL_CLASS_NAMES);

const SOP_INSTANCE_UID = "00080018";
const SERIES_INSTANCE_UID = "0020000E";
const NUMBER_OF_FRAMES = "00280008";
const MODALITY = "00080060";

/**
 * Build `wadors:` imageIds for a DICOMweb series and cache its metadata.
 *
 * This is a self-contained equivalent of the Cornerstone3D repository helper
 * `utils/demo/helpers/createImageIdsAndCacheMetaData.js`, which is not
 * published to npm.
 *
 * @param {object} args Query arguments.
 * @param {string} args.wadoRsRoot The DICOMweb (WADO-RS) root URL.
 * @param {string} args.StudyInstanceUID Study to query.
 * @param {string} args.SeriesInstanceUID Series to query.
 * @param {string} [args.SOPInstanceUID] Restrict to a single instance.
 * @param {object} args.loader The `@cornerstonejs/dicom-image-loader` module.
 * @param {Record<string, string>} [args.headers] Extra request headers.
 * @returns {Promise<{imageIds: string[], modality: string, instances: object[]}>}
 */
export async function createImageIds({
  wadoRsRoot,
  StudyInstanceUID,
  SeriesInstanceUID,
  SOPInstanceUID = null,
  loader,
  headers = {},
}) {
  const { api } = await import("dicomweb-client");
  const client = new api.DICOMwebClient({
    url: wadoRsRoot,
    headers: { ...headersFor(wadoRsRoot), ...headers },
  });

  let instances = await client.retrieveSeriesMetadata({
    studyInstanceUID: StudyInstanceUID,
    seriesInstanceUID: SeriesInstanceUID,
  });

  if (SOPInstanceUID) {
    instances = instances.filter(
      (inst) => inst[SOP_INSTANCE_UID]?.Value?.[0] === SOPInstanceUID
    );
  }
  if (!instances.length) {
    throw new Error(
      `No instances returned for series ${SeriesInstanceUID} of study ${StudyInstanceUID}`
    );
  }

  // Sort by InstanceNumber when present so the stack is in acquisition order.
  const INSTANCE_NUMBER = "00200013";
  instances.sort((a, b) => {
    const na = Number(a[INSTANCE_NUMBER]?.Value?.[0] ?? 0);
    const nb = Number(b[INSTANCE_NUMBER]?.Value?.[0] ?? 0);
    return na - nb;
  });

  let addDicomWebInstance = null;
  try {
    const metadataModule = await import("@cornerstonejs/metadata");
    addDicomWebInstance = metadataModule.utilities?.addDicomWebInstance ?? null;
  } catch {
    /* @cornerstonejs/metadata not installed: the legacy provider still works */
  }

  const imageIds = [];
  for (const inst of instances) {
    const seriesUid = inst[SERIES_INSTANCE_UID].Value[0];
    const sopUid = inst[SOP_INSTANCE_UID].Value[0];
    const base =
      `wadors:${wadoRsRoot}/studies/${StudyInstanceUID.trim()}` +
      `/series/${seriesUid.trim()}/instances/${sopUid.trim()}/frames/`;
    const numFrames = Number(inst[NUMBER_OF_FRAMES]?.Value?.[0] ?? 1) || 1;
    for (let frame = 1; frame <= numFrames; frame += 1) {
      const imageId = base + frame;
      loader.wadors.metaDataManager.add(imageId, inst);
      if (addDicomWebInstance) {
        try {
          addDicomWebInstance(imageId, inst);
        } catch {
          /* non-fatal: the legacy wadors provider already has the instance */
        }
      }
      imageIds.push(imageId);
    }
  }

  return {
    imageIds,
    modality: instances[0][MODALITY]?.Value?.[0] ?? "",
    instances,
  };
}

/**
 * Convert a window width / center pair into a Cornerstone `voiRange`.
 *
 * @param {number} width Window width.
 * @param {number} center Window center.
 * @returns {{lower: number, upper: number}} The VOI range.
 */
export function windowToVoiRange(width, center) {
  return { lower: center - width / 2, upper: center + width / 2 };
}

/**
 * Convert a Cornerstone `voiRange` into a window width / center pair.
 *
 * @param {{lower: number, upper: number}} range The VOI range.
 * @returns {{windowWidth: number, windowCenter: number}} Window values.
 */
export function voiRangeToWindow(range) {
  if (!range) {
    return { windowWidth: 0, windowCenter: 0 };
  }
  return {
    windowWidth: range.upper - range.lower,
    windowCenter: (range.upper + range.lower) / 2,
  };
}

/**
 * Flatten Cornerstone annotations into plain, JSON-serialisable measurements
 * suitable for sending to a Reflex backend state.
 *
 * @param {object} tools The `@cornerstonejs/tools` module.
 * @returns {object[]} One entry per annotation.
 */
export function collectMeasurements(tools) {
  let annotations = [];
  try {
    annotations = tools.annotation.state.getAllAnnotations() || [];
  } catch {
    return [];
  }
  return annotations.map((ann) => {
    const cachedStats = ann?.data?.cachedStats ?? {};
    const firstKey = Object.keys(cachedStats)[0];
    const stats = firstKey ? cachedStats[firstKey] : {};
    const plainStats = {};
    for (const [key, value] of Object.entries(stats || {})) {
      if (typeof value === "number" || typeof value === "string") {
        plainStats[key] = value;
      }
    }
    return {
      uid: ann.annotationUID,
      toolName: ann?.metadata?.toolName ?? "",
      label: ann?.data?.label ?? ann?.data?.text ?? "",
      frameOfReferenceUID: ann?.metadata?.FrameOfReferenceUID ?? "",
      referencedImageId: ann?.metadata?.referencedImageId ?? "",
      stats: plainStats,
    };
  });
}

/**
 * Register a viewer instance so Python can drive it through `rx.call_script`.
 *
 * @param {string} viewportId The viewport id used as the registry key.
 * @param {object} api The imperative API object exposed to callers.
 */
export function registerViewer(viewportId, api) {
  viewerRegistry[viewportId] = api;
}

/**
 * Remove a viewer instance from the registry.
 *
 * @param {string} viewportId The viewport id to forget.
 */
export function unregisterViewer(viewportId) {
  delete viewerRegistry[viewportId];
}
