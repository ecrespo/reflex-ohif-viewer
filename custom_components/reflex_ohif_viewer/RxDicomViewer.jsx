/**
 * RxDicomViewer — a self-contained Cornerstone3D viewport for Reflex.
 *
 * Cornerstone3D is the rendering and tooling engine that powers the OHIF
 * Viewer. OHIF itself ships no importable React component, so this component
 * wraps the engine directly and exposes it to Reflex through props, events and
 * a small imperative API registered on `window.__rxDicomViewers`.
 *
 * Every Cornerstone module is pulled in with a dynamic `import()` from inside
 * an effect, so nothing runs during server-side rendering or prerendering.
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  collectMeasurements,
  createImageIds,
  ensureCornerstone,
  registerHeaders,
  registerViewer,
  resolveToolName,
  unregisterViewer,
  voiRangeToWindow,
  windowToVoiRange,
} from "./rxCornerstoneRuntime.js";

/** Tools that are always given the primary mouse button when selected. */
const DEFAULT_TOOLS = [
  "WindowLevel",
  "Pan",
  "Zoom",
  "StackScroll",
  "Length",
  "RectangleROI",
  "EllipticalROI",
  "CircleROI",
  "Bidirectional",
  "Angle",
  "ArrowAnnotate",
  "Probe",
  "PlanarFreehandROI",
  "Magnify",
  "Eraser",
];

/** Tools that should never be demoted when the primary tool changes. */
const NAVIGATION_TOOLS = new Set(["Pan", "Zoom", "StackScroll"]);

const DICOM_TAGS = {
  patientName: "00100010",
  patientId: "00100020",
  studyDate: "00080020",
  studyDescription: "00081030",
  seriesDescription: "0008103E",
  seriesNumber: "00200011",
  modality: "00080060",
  institutionName: "00080080",
  manufacturer: "00080070",
  rows: "00280010",
  columns: "00280011",
};

/**
 * Pull a handful of human-readable fields out of a DICOM-JSON instance.
 *
 * @param {object} instance A DICOM-JSON (QIDO/WADO metadata) instance.
 * @returns {Record<string, string>} Plain string values, missing tags omitted.
 */
function describeInstance(instance) {
  const out = {};
  if (!instance) {
    return out;
  }
  for (const [name, tag] of Object.entries(DICOM_TAGS)) {
    const value = instance[tag]?.Value?.[0];
    if (value === undefined || value === null) {
      continue;
    }
    out[name] = typeof value === "object" ? (value.Alphabetic ?? "") : String(value);
  }
  return out;
}

/**
 * Stable stringification used to decide whether a list/object prop changed.
 *
 * @param {unknown} value Any JSON-serialisable value.
 * @returns {string} A comparable string.
 */
function signature(value) {
  try {
    return JSON.stringify(value ?? null);
  } catch {
    return String(value);
  }
}

export default function RxDicomViewer({
  // --- data ------------------------------------------------------------
  imageIds: imageIdsProp = null,
  wadoRsRoot = "",
  studyInstanceUid = "",
  seriesInstanceUid = "",
  sopInstanceUid = "",
  headers = null,

  // --- identity --------------------------------------------------------
  viewportId = "rx-dicom-viewport",
  renderingEngineId = "rx-dicom-rendering-engine",
  toolGroupId = "",
  volumeId = "",

  // --- rendering -------------------------------------------------------
  mode = "stack",
  orientation = "axial",
  background = null,
  initialImageIndex = -1,
  voiRange = null,
  windowWidth = 0,
  windowCenter = 0,
  invert = false,
  colormap = "",
  preset = "",
  slabThickness = 0,

  // --- tools -----------------------------------------------------------
  tools = null,
  activeTool = "WindowLevel",

  // --- runtime ---------------------------------------------------------
  maxWebWorkers = 0,
  wasmBasePath = "",
  cine = false,
  cineFramesPerSecond = 24,
  cineLoop = true,

  // --- presentation ----------------------------------------------------
  showOverlay = true,
  showLoadingIndicator = true,
  overlayColor = "#9ae6b4",
  className = "",
  style = null,

  // --- events ----------------------------------------------------------
  onViewerReady,
  onSliceChange,
  onVoiChange,
  onMeasurementsChange,
  onAnnotationAdded,
  onAnnotationModified,
  onAnnotationRemoved,
  onLoadProgress,
  onError,
}) {
  const elementRef = useRef(null);
  const runtimeRef = useRef(null);
  const [status, setStatus] = useState("idle");
  const [errorText, setErrorText] = useState("");
  const [info, setInfo] = useState({
    index: 0,
    total: 0,
    windowWidth: 0,
    windowCenter: 0,
    zoom: 1,
    meta: {},
  });

  // Keep the latest event handlers in a ref so the setup effect does not
  // re-run every time Reflex hands us new closures.
  const handlersRef = useRef({});
  handlersRef.current = {
    onViewerReady,
    onSliceChange,
    onVoiChange,
    onMeasurementsChange,
    onAnnotationAdded,
    onAnnotationModified,
    onAnnotationRemoved,
    onLoadProgress,
    onError,
  };

  const toolList = useMemo(
    () => (Array.isArray(tools) && tools.length ? tools : DEFAULT_TOOLS),
    [signature(tools)] // eslint-disable-line react-hooks/exhaustive-deps
  );
  const resolvedToolGroupId = toolGroupId || `${viewportId}-tools`;
  const imageIdsSignature = signature(imageIdsProp);
  const headersSignature = signature(headers);
  const toolsSignature = signature(toolList);

  const emitError = useCallback((err) => {
    const message = err?.message ? String(err.message) : String(err);
    setErrorText(message);
    setStatus("error");
    handlersRef.current.onError?.(message);
    // Surface it in the console too: Reflex apps often have no error UI.
    console.error("[reflex-ohif-viewer]", err);
  }, []);

  const pushMeasurements = useCallback(() => {
    const runtime = runtimeRef.current;
    if (!runtime?.tools || !handlersRef.current.onMeasurementsChange) {
      return;
    }
    handlersRef.current.onMeasurementsChange(collectMeasurements(runtime.tools));
  }, []);

  // ---------------------------------------------------------------- setup
  useEffect(() => {
    const element = elementRef.current;
    if (!element) {
      return undefined;
    }

    let cancelled = false;
    const cleanups = [];

    (async () => {
      try {
        setStatus("initializing");
        setErrorText("");

        if (headers && wadoRsRoot) {
          registerHeaders(wadoRsRoot, headers);
        }

        const { core, tools: csTools, loader } = await ensureCornerstone({
          maxWebWorkers: maxWebWorkers || undefined,
          wasmBasePath: wasmBasePath || undefined,
        });
        if (cancelled) {
          return;
        }

        const { Enums, RenderingEngine, getRenderingEngine, volumeLoader, setVolumesForViewports, eventTarget, utilities: csUtils } = core;
        const { ToolGroupManager, Enums: toolsEnums, utilities: csToolsUtils, annotation } = csTools;
        const { MouseBindings, KeyboardBindings } = toolsEnums;

        // ---- resolve image ids -------------------------------------
        setStatus("loading-metadata");
        let imageIds = Array.isArray(imageIdsProp) ? imageIdsProp.filter(Boolean) : [];
        let seriesMeta = {};
        if (!imageIds.length) {
          if (!wadoRsRoot || !studyInstanceUid || !seriesInstanceUid) {
            setStatus("empty");
            return;
          }
          const result = await createImageIds({
            wadoRsRoot,
            StudyInstanceUID: studyInstanceUid,
            SeriesInstanceUID: seriesInstanceUid,
            SOPInstanceUID: sopInstanceUid || null,
            loader,
            headers: headers || {},
          });
          imageIds = result.imageIds;
          seriesMeta = describeInstance(result.instances[0]);
        }
        if (cancelled || !imageIds.length) {
          if (!imageIds.length) {
            setStatus("empty");
          }
          return;
        }

        // ---- rendering engine + viewport ---------------------------
        setStatus("rendering");
        let renderingEngine = getRenderingEngine(renderingEngineId);
        if (!renderingEngine) {
          renderingEngine = new RenderingEngine(renderingEngineId);
        }

        const isVolume = mode === "volume" || mode === "volume3d";
        const viewportType =
          mode === "volume3d"
            ? Enums.ViewportType.VOLUME_3D
            : isVolume
              ? Enums.ViewportType.ORTHOGRAPHIC
              : Enums.ViewportType.STACK;

        const defaultOptions = {
          background: Array.isArray(background) && background.length === 3 ? background : [0, 0, 0],
        };
        if (mode === "volume") {
          const axis = String(orientation || "axial").toUpperCase();
          defaultOptions.orientation = Enums.OrientationAxis[axis] ?? Enums.OrientationAxis.AXIAL;
        }

        renderingEngine.enableElement({ viewportId, element, type: viewportType, defaultOptions });
        cleanups.push(() => {
          try {
            renderingEngine.disableElement(viewportId);
          } catch {
            /* engine already torn down */
          }
        });

        // ---- tool group --------------------------------------------
        let toolGroup = ToolGroupManager.getToolGroup(resolvedToolGroupId);
        if (!toolGroup) {
          toolGroup = ToolGroupManager.createToolGroup(resolvedToolGroupId);
        }
        const toolNames = {};
        for (const publicName of toolList) {
          const csName = resolveToolName(csTools, publicName);
          if (!csName) {
            console.warn(`[reflex-ohif-viewer] unknown tool "${publicName}" ignored`);
            continue;
          }
          toolNames[publicName] = csName;
          if (!toolGroup.hasTool?.(csName)) {
            try {
              toolGroup.addTool(csName);
            } catch (err) {
              console.warn(`[reflex-ohif-viewer] could not add tool "${publicName}":`, err);
            }
          }
        }

        /** Give the navigation tools their permanent, non-primary bindings. */
        const applyNavigationBindings = () => {
          if (toolNames.Zoom) {
            toolGroup.setToolActive(toolNames.Zoom, {
              bindings: [{ mouseButton: MouseBindings.Secondary }],
            });
          }
          if (toolNames.Pan) {
            toolGroup.setToolActive(toolNames.Pan, {
              bindings: [
                { mouseButton: MouseBindings.Auxiliary },
                { mouseButton: MouseBindings.Primary, modifierKey: KeyboardBindings.Ctrl },
              ],
            });
          }
          if (toolNames.StackScroll) {
            toolGroup.setToolActive(toolNames.StackScroll, {
              bindings: [
                { mouseButton: MouseBindings.Wheel },
                { mouseButton: MouseBindings.Primary, modifierKey: KeyboardBindings.Alt },
              ],
            });
          }
        };

        /** Put `publicName` on the primary mouse button, demoting the rest. */
        const setPrimaryTool = (publicName) => {
          const csName = toolNames[publicName] ?? resolveToolName(csTools, publicName);
          if (!csName) {
            return;
          }
          for (const [name, resolved] of Object.entries(toolNames)) {
            if (name !== publicName && !NAVIGATION_TOOLS.has(name)) {
              try {
                toolGroup.setToolPassive(resolved);
              } catch {
                /* tool not in this group */
              }
            }
          }
          try {
            toolGroup.setToolActive(csName, {
              bindings: [{ mouseButton: MouseBindings.Primary }],
            });
          } catch (err) {
            console.warn(`[reflex-ohif-viewer] could not activate "${publicName}":`, err);
          }
          applyNavigationBindings();
        };

        applyNavigationBindings();
        setPrimaryTool(activeTool);
        toolGroup.addViewport(viewportId, renderingEngineId);
        cleanups.push(() => {
          try {
            toolGroup.removeViewports(renderingEngineId, viewportId);
          } catch {
            /* already removed */
          }
        });

        // ---- load pixel data ---------------------------------------
        const viewport = renderingEngine.getViewport(viewportId);
        const startIndex =
          initialImageIndex >= 0
            ? Math.min(initialImageIndex, imageIds.length - 1)
            : Math.floor(imageIds.length / 2);

        const resolvedVolumeId =
          volumeId ||
          `cornerstoneStreamingImageVolume:${viewportId}-${seriesInstanceUid || imageIds.length}`;

        if (isVolume) {
          const volume = await volumeLoader.createAndCacheVolume(resolvedVolumeId, { imageIds });
          if (cancelled) {
            return;
          }
          volume.load?.();
          await setVolumesForViewports(renderingEngine, [{ volumeId: resolvedVolumeId }], [viewportId]);
        } else {
          await viewport.setStack(imageIds, startIndex);
        }
        if (cancelled) {
          return;
        }

        // ---- display properties ------------------------------------
        const properties = {};
        if (voiRange && typeof voiRange.lower === "number" && typeof voiRange.upper === "number") {
          properties.voiRange = { lower: voiRange.lower, upper: voiRange.upper };
        } else if (windowWidth > 0) {
          properties.voiRange = windowToVoiRange(windowWidth, windowCenter);
        }
        if (invert) {
          properties.invert = true;
        }
        if (colormap) {
          properties.colormap = { name: colormap };
        }
        if (mode === "volume3d" && preset) {
          properties.preset = preset;
        }
        if (Object.keys(properties).length) {
          try {
            viewport.setProperties(properties);
          } catch (err) {
            console.warn("[reflex-ohif-viewer] setProperties failed:", err);
          }
        }
        if (isVolume && slabThickness > 0 && viewport.setSlabThickness) {
          viewport.setSlabThickness(slabThickness);
        }
        viewport.render();

        // ---- live info ---------------------------------------------
        /** Read the current slice / VOI / zoom state off the viewport. */
        const readState = () => {
          let index = 0;
          let total = imageIds.length;
          try {
            if (typeof viewport.getCurrentImageIdIndex === "function") {
              index = viewport.getCurrentImageIdIndex() ?? 0;
            } else if (csUtils.getVolumeViewportScrollInfo) {
              const scroll = csUtils.getVolumeViewportScrollInfo(viewport, resolvedVolumeId);
              index = scroll?.currentStepIndex ?? 0;
              total = scroll?.numScrollSteps ?? total;
            }
          } catch {
            /* viewport not ready yet */
          }
          let window = { windowWidth: 0, windowCenter: 0 };
          try {
            window = voiRangeToWindow(viewport.getProperties()?.voiRange);
          } catch {
            /* no VOI yet */
          }
          let zoom = 1;
          try {
            zoom = viewport.getZoom?.() ?? 1;
          } catch {
            /* no camera yet */
          }
          return { index, total, ...window, zoom };
        };

        const publishState = () => {
          const next = readState();
          setInfo((prev) => ({ ...prev, ...next, meta: seriesMeta }));
          return next;
        };

        // ---- events -------------------------------------------------
        const onNewImage = () => {
          const next = publishState();
          handlersRef.current.onSliceChange?.({ index: next.index, total: next.total });
        };
        const onVoi = () => {
          const next = publishState();
          handlersRef.current.onVoiChange?.({
            windowWidth: next.windowWidth,
            windowCenter: next.windowCenter,
          });
        };
        const onCamera = () => publishState();

        element.addEventListener(Enums.Events.STACK_NEW_IMAGE, onNewImage);
        element.addEventListener(Enums.Events.VOLUME_NEW_IMAGE, onNewImage);
        element.addEventListener(Enums.Events.VOI_MODIFIED, onVoi);
        element.addEventListener(Enums.Events.CAMERA_MODIFIED, onCamera);
        cleanups.push(() => {
          element.removeEventListener(Enums.Events.STACK_NEW_IMAGE, onNewImage);
          element.removeEventListener(Enums.Events.VOLUME_NEW_IMAGE, onNewImage);
          element.removeEventListener(Enums.Events.VOI_MODIFIED, onVoi);
          element.removeEventListener(Enums.Events.CAMERA_MODIFIED, onCamera);
        });

        const annotationHandler = (kind) => (evt) => {
          const detail = evt?.detail ?? {};
          const payload = {
            uid: detail.annotation?.annotationUID ?? detail.annotationUID ?? "",
            toolName: detail.annotation?.metadata?.toolName ?? "",
          };
          if (kind === "added") {
            handlersRef.current.onAnnotationAdded?.(payload);
          } else if (kind === "modified") {
            handlersRef.current.onAnnotationModified?.(payload);
          } else {
            handlersRef.current.onAnnotationRemoved?.(payload);
          }
          pushMeasurements();
        };
        const added = annotationHandler("added");
        const modified = annotationHandler("modified");
        const removed = annotationHandler("removed");
        eventTarget.addEventListener(toolsEnums.Events.ANNOTATION_COMPLETED, added);
        eventTarget.addEventListener(toolsEnums.Events.ANNOTATION_MODIFIED, modified);
        eventTarget.addEventListener(toolsEnums.Events.ANNOTATION_REMOVED, removed);
        cleanups.push(() => {
          eventTarget.removeEventListener(toolsEnums.Events.ANNOTATION_COMPLETED, added);
          eventTarget.removeEventListener(toolsEnums.Events.ANNOTATION_MODIFIED, modified);
          eventTarget.removeEventListener(toolsEnums.Events.ANNOTATION_REMOVED, removed);
        });

        if (handlersRef.current.onLoadProgress) {
          let loaded = 0;
          const onImageLoaded = () => {
            loaded += 1;
            handlersRef.current.onLoadProgress?.({ loaded, total: imageIds.length });
          };
          eventTarget.addEventListener(Enums.Events.IMAGE_LOADED, onImageLoaded);
          cleanups.push(() => eventTarget.removeEventListener(Enums.Events.IMAGE_LOADED, onImageLoaded));
        }

        // Cornerstone never resizes itself; mirror the container instead.
        const observer = new ResizeObserver(() => {
          try {
            renderingEngine.resize(true, false);
          } catch {
            /* engine disposed */
          }
        });
        observer.observe(element);
        cleanups.push(() => observer.disconnect());

        // Escape cancels a half-drawn annotation.
        const onKeyDown = (event) => {
          if (event.key === "Escape") {
            try {
              csTools.cancelActiveManipulations(element);
            } catch {
              /* nothing in progress */
            }
          }
        };
        element.addEventListener("keydown", onKeyDown);
        cleanups.push(() => element.removeEventListener("keydown", onKeyDown));

        // ---- imperative API ----------------------------------------
        const api = {
          viewportId,
          renderingEngineId,
          toolGroupId: resolvedToolGroupId,
          getViewport: () => renderingEngine.getViewport(viewportId),
          setTool: (name) => setPrimaryTool(name),
          resetCamera: () => {
            viewport.resetCamera();
            viewport.render();
            publishState();
          },
          resetProperties: () => {
            viewport.resetProperties?.();
            viewport.render();
            publishState();
          },
          jumpToSlice: async (index) => {
            try {
              await csUtils.jumpToSlice(element, { imageIndex: index });
            } catch (err) {
              console.warn("[reflex-ohif-viewer] jumpToSlice failed:", err);
            }
            publishState();
          },
          scroll: (delta) => {
            try {
              viewport.scroll?.(delta);
            } catch {
              /* out of bounds */
            }
            publishState();
          },
          setVoiRange: (range) => {
            viewport.setProperties({ voiRange: range });
            viewport.render();
            publishState();
          },
          setWindow: (width, center) => {
            viewport.setProperties({ voiRange: windowToVoiRange(width, center) });
            viewport.render();
            publishState();
          },
          setInvert: (value) => {
            viewport.setProperties({ invert: !!value });
            viewport.render();
          },
          setColormap: (name) => {
            viewport.setProperties({ colormap: name ? { name } : undefined });
            viewport.render();
          },
          setZoom: (value) => {
            viewport.setZoom?.(value);
            viewport.render();
            publishState();
          },
          rotate: (degrees) => {
            try {
              viewport.setViewPresentation?.({ rotation: degrees });
            } catch {
              /* stack viewports only */
            }
            viewport.render();
          },
          flip: ({ horizontal = false, vertical = false } = {}) => {
            const camera = viewport.getCamera();
            viewport.setCamera({
              ...camera,
              flipHorizontal: horizontal ? !camera.flipHorizontal : camera.flipHorizontal,
              flipVertical: vertical ? !camera.flipVertical : camera.flipVertical,
            });
            viewport.render();
          },
          setSlabThickness: (value) => {
            viewport.setSlabThickness?.(value);
            viewport.render();
          },
          setOrientation: (axis) => {
            viewport.setOrientation?.(Enums.OrientationAxis[String(axis).toUpperCase()]);
            viewport.render();
          },
          playCine: (fps = cineFramesPerSecond, loop = cineLoop) => {
            csToolsUtils.cine.playClip(element, { framesPerSecond: fps, loop });
          },
          stopCine: () => csToolsUtils.cine.stopClip(element),
          getMeasurements: () => collectMeasurements(csTools),
          removeMeasurement: (uid) => {
            annotation.state.removeAnnotation(uid);
            viewport.render();
            pushMeasurements();
          },
          clearMeasurements: () => {
            annotation.state.removeAllAnnotations();
            viewport.render();
            pushMeasurements();
          },
          captureScreenshot: () => element.querySelector("canvas")?.toDataURL("image/png") ?? "",
          getImageIds: () => imageIds.slice(),
          getState: () => readState(),
          render: () => viewport.render(),
        };
        registerViewer(viewportId, api);
        cleanups.push(() => unregisterViewer(viewportId));
        runtimeRef.current = {
          core,
          tools: csTools,
          api,
          viewport,
          element,
          setPrimaryTool,
          imageIds,
          isVolume,
        };

        const initial = publishState();
        setStatus("ready");
        handlersRef.current.onViewerReady?.({
          viewportId,
          toolGroupId: resolvedToolGroupId,
          numImages: imageIds.length,
          index: initial.index,
          mode,
          ...seriesMeta,
        });
        if (cine) {
          csToolsUtils.cine.playClip(element, {
            framesPerSecond: cineFramesPerSecond,
            loop: cineLoop,
          });
        }
      } catch (err) {
        if (!cancelled) {
          emitError(err);
        }
      }
    })();

    return () => {
      cancelled = true;
      runtimeRef.current = null;
      for (const cleanup of cleanups.reverse()) {
        try {
          cleanup();
        } catch {
          /* best effort */
        }
      }
    };
    // Re-create the viewport when the data or its structural identity changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    imageIdsSignature,
    wadoRsRoot,
    studyInstanceUid,
    seriesInstanceUid,
    sopInstanceUid,
    headersSignature,
    viewportId,
    renderingEngineId,
    resolvedToolGroupId,
    volumeId,
    mode,
    orientation,
    toolsSignature,
    maxWebWorkers,
    wasmBasePath,
  ]);

  // ------------------------------------------------- reactive prop updates
  useEffect(() => {
    runtimeRef.current?.setPrimaryTool?.(activeTool);
  }, [activeTool, status]);

  useEffect(() => {
    const api = runtimeRef.current?.api;
    if (!api || status !== "ready") {
      return;
    }
    if (voiRange && typeof voiRange.lower === "number" && typeof voiRange.upper === "number") {
      api.setVoiRange({ lower: voiRange.lower, upper: voiRange.upper });
    } else if (windowWidth > 0) {
      api.setWindow(windowWidth, windowCenter);
    }
  }, [signature(voiRange), windowWidth, windowCenter, status]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (status === "ready") {
      runtimeRef.current?.api?.setInvert(invert);
    }
  }, [invert, status]);

  useEffect(() => {
    if (status === "ready") {
      runtimeRef.current?.api?.setColormap(colormap);
    }
  }, [colormap, status]);

  useEffect(() => {
    const api = runtimeRef.current?.api;
    if (!api || status !== "ready") {
      return undefined;
    }
    if (cine) {
      api.playCine(cineFramesPerSecond, cineLoop);
      return () => api.stopCine();
    }
    api.stopCine();
    return undefined;
  }, [cine, cineFramesPerSecond, cineLoop, status]);

  // The viewport element must never be a React-managed subtree: Cornerstone
  // appends its own canvas children to it.
  useLayoutEffect(() => {
    const element = elementRef.current;
    if (element) {
      element.oncontextmenu = (event) => event.preventDefault();
    }
  }, []);

  const containerStyle = {
    position: "relative",
    width: "100%",
    height: "100%",
    minHeight: "240px",
    background: "#000",
    overflow: "hidden",
    ...(style || {}),
  };

  const overlayBase = {
    position: "absolute",
    color: overlayColor,
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
    fontSize: "11px",
    lineHeight: 1.45,
    pointerEvents: "none",
    textShadow: "0 1px 2px rgba(0,0,0,0.9)",
    whiteSpace: "pre",
    zIndex: 2,
  };

  const busy = status !== "ready" && status !== "error" && status !== "empty";

  return (
    <div className={className} style={containerStyle}>
      <div
        ref={elementRef}
        tabIndex={0}
        style={{ width: "100%", height: "100%", outline: "none" }}
        data-viewport-id={viewportId}
        data-status={status}
      />

      {showOverlay && status === "ready" && (
        <>
          <div style={{ ...overlayBase, top: 8, left: 8 }}>
            {[info.meta.patientName, info.meta.patientId && `ID ${info.meta.patientId}`]
              .filter(Boolean)
              .join("\n")}
          </div>
          <div style={{ ...overlayBase, top: 8, right: 8, textAlign: "right" }}>
            {[info.meta.studyDescription, info.meta.studyDate, info.meta.institutionName]
              .filter(Boolean)
              .join("\n")}
          </div>
          <div style={{ ...overlayBase, bottom: 8, left: 8 }}>
            {[
              info.meta.modality &&
                `${info.meta.modality}${info.meta.seriesNumber ? ` · Se ${info.meta.seriesNumber}` : ""}`,
              info.meta.seriesDescription,
              info.total ? `Im ${info.index + 1}/${info.total}` : "",
            ]
              .filter(Boolean)
              .join("\n")}
          </div>
          <div style={{ ...overlayBase, bottom: 8, right: 8, textAlign: "right" }}>
            {[
              info.windowWidth
                ? `W ${Math.round(info.windowWidth)} L ${Math.round(info.windowCenter)}`
                : "",
              `Zoom ${info.zoom.toFixed(2)}x`,
            ]
              .filter(Boolean)
              .join("\n")}
          </div>
        </>
      )}

      {showLoadingIndicator && busy && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: overlayColor,
            font: "13px ui-monospace, SFMono-Regular, Menlo, monospace",
            pointerEvents: "none",
            zIndex: 3,
          }}
        >
          {status.replace(/-/g, " ")}…
        </div>
      )}

      {status === "empty" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#64748b",
            font: "13px ui-monospace, SFMono-Regular, Menlo, monospace",
          }}
        >
          No series selected
        </div>
      )}

      {status === "error" && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "16px",
            color: "#fca5a5",
            font: "12px ui-monospace, SFMono-Regular, Menlo, monospace",
            textAlign: "center",
            overflow: "auto",
          }}
        >
          {errorText}
        </div>
      )}
    </div>
  );
}
