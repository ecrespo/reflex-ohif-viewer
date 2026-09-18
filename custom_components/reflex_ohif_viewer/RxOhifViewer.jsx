/**
 * RxOhifViewer — embeds a self-hosted OHIF Viewer v3 build in an iframe.
 *
 * OHIF v3 publishes no importable React component (`@ohif/app` on npm is a
 * prebuilt static site whose `main` field points at a file the tarball does not
 * contain) and defines no postMessage protocol. The supported integration is an
 * iframe driven by URL query parameters, which `./rxOhifUrl.js` builds.
 */

import { useCallback, useEffect, useMemo, useRef } from "react";

import { buildOhifUrl } from "./rxOhifUrl.js";

export { buildOhifUrl };

export default function RxOhifViewer({
  baseUrl = "",
  title = "OHIF Viewer",
  allow = "cross-origin-isolated; fullscreen; clipboard-read; clipboard-write",
  sandbox = "",
  referrerPolicy = "no-referrer-when-downgrade",
  className = "",
  style = null,
  onViewerLoad,
  onViewerMessage,
  onUrlChange,
  // Everything else feeds the URL builder.
  ...urlProps
}) {
  const iframeRef = useRef(null);
  const url = useMemo(() => buildOhifUrl({ baseUrl, ...urlProps }), [
    baseUrl,
    JSON.stringify(urlProps),
  ]);

  useEffect(() => {
    if (url) {
      onUrlChange?.(url);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);

  // OHIF upstream never posts messages to its parent. This listener exists so
  // that a deployment which *adds* its own OHIF extension (or serves OHIF
  // same-origin behind a small shim) can talk back to the Reflex state.
  useEffect(() => {
    if (!onViewerMessage || typeof window === "undefined") {
      return undefined;
    }
    let origin = "";
    try {
      origin = new URL(url, window.location.href).origin;
    } catch {
      origin = "";
    }
    const handler = (event) => {
      if (origin && event.origin !== origin) {
        return;
      }
      if (iframeRef.current && event.source !== iframeRef.current.contentWindow) {
        return;
      }
      let payload = event.data;
      if (typeof payload !== "string") {
        try {
          payload = JSON.stringify(payload);
        } catch {
          payload = String(payload);
        }
      }
      onViewerMessage(payload);
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, onViewerMessage]);

  const handleLoad = useCallback(() => {
    onViewerLoad?.(url);
  }, [onViewerLoad, url]);

  const frameStyle = {
    width: "100%",
    height: "100%",
    minHeight: "480px",
    border: "none",
    display: "block",
    background: "#000",
    ...(style || {}),
  };

  if (!url) {
    return (
      <div
        className={className}
        style={{
          ...frameStyle,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#94a3b8",
          font: "13px ui-monospace, SFMono-Regular, Menlo, monospace",
          textAlign: "center",
          padding: "16px",
        }}
      >
        Set `base_url` to a running OHIF Viewer build
        {"\n"}(for example `docker run -p 3001:80 ohif/app:v3.13.8`).
      </div>
    );
  }

  return (
    <iframe
      ref={iframeRef}
      src={url}
      title={title}
      className={className}
      style={frameStyle}
      allow={allow}
      referrerPolicy={referrerPolicy}
      {...(sandbox ? { sandbox } : {})}
      onLoad={handleLoad}
    />
  );
}
