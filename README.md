# reflex-ohif-viewer

[![CI](https://github.com/ecrespo/reflex-ohif-viewer/actions/workflows/ci.yml/badge.svg)](https://github.com/ecrespo/reflex-ohif-viewer/actions/workflows/ci.yml)
[![Security](https://github.com/ecrespo/reflex-ohif-viewer/actions/workflows/security.yml/badge.svg)](https://github.com/ecrespo/reflex-ohif-viewer/actions/workflows/security.yml)
[![CodeQL](https://github.com/ecrespo/reflex-ohif-viewer/actions/workflows/codeql.yml/badge.svg)](https://github.com/ecrespo/reflex-ohif-viewer/actions/workflows/codeql.yml)
[![PyPI](https://img.shields.io/pypi/v/reflex-ohif-viewer)](https://pypi.org/project/reflex-ohif-viewer/)
[![Python](https://img.shields.io/pypi/pyversions/reflex-ohif-viewer)](https://pypi.org/project/reflex-ohif-viewer/)
[![License: MIT](https://img.shields.io/badge/licence-MIT-blue.svg)](LICENSE)

DICOM viewing for [Reflex](https://reflex.dev) apps, two ways: the
[OHIF Viewer v3](https://ohif.org/) embedded as an iframe, and
[Cornerstone3D](https://www.cornerstonejs.org/) — the engine OHIF renders with —
wrapped as a native Reflex component.

```bash
pip install reflex-ohif-viewer
```

```python
import reflex as rx
from reflex_ohif_viewer import PUBLIC_DICOMWEB_ROOT, dicom_viewer


def index() -> rx.Component:
    return dicom_viewer(
        wado_rs_root=PUBLIC_DICOMWEB_ROOT,
        study_instance_uid="1.3.6.1.4.1.14519.5.2.1.7009.2403.334240657131972136850343327463",
        series_instance_uid="1.3.6.1.4.1.14519.5.2.1.7009.2403.226151125820845824875394858561",
        viewport_id="main",
        active_tool="Length",
        height="70vh",
    )
```

---

## Which component do you want?

|  | `ohif_viewer()` | `dicom_viewer()` |
|---|---|---|
| What it is | A self-hosted OHIF v3 build in an iframe | A Cornerstone3D viewport in your component tree |
| You get | The whole OHIF product: study list, hanging protocols, measurement tracking, segmentation, TMTV, microscopy | One viewport, and full control of the UI around it |
| Reflex state | One-way. Props build the URL; OHIF exposes no cross-frame API | Two-way. Props drive it; slice, window/level and annotations come back as events |
| Deployment | A separate OHIF build to host | npm packages installed into the Reflex frontend |
| Reach for it when | You want a full diagnostic viewer and don't need Python in the loop | The viewer is part of your app and Python needs to read and drive it |

You can use both in the same app.

---

## What the research found

These are checked against the OHIF 3.13.8 source and the published npm tarballs,
not against the documentation — which lags the code by several minor versions.

**OHIF publishes no importable React component.** `@ohif/app` on npm is a
prebuilt static site: its `package.json` sets `main` to `dist/index.umd.js`, a
file the tarball does not contain, and `module` to source that is not published.
There is no web component either (`customElements.define` appears nowhere in
`platform/`, `extensions/` or `modes/`). `@ohif/viewer` is OHIF v2 and was last
published in 2023.

**OHIF has no postMessage API.** Its own source never posts to a parent frame and
never listens for a message from one. The four mentions of `postMessage` in its
docs describe something *you* may implement. The `ohif_viewer` component
therefore builds a URL and nothing more — and says so, rather than implying an
API that does not exist.

**Cornerstone3D is the way to get two-way binding.** It is published as real npm
libraries (`@cornerstonejs/core`, `tools`, `dicom-image-loader` at 5.10.6), and
`dicom_viewer` wraps them directly.

**No existing React wrapper was worth using.** `@cornerstonejs/react` and
`react-cornerstone3d` do not exist on npm. `react-cornerstone-viewport` targets
the abandoned legacy cornerstone and has not been released since 2022.
`@ohif/ui-next` is OHIF's shadcn/Radix design system with no viewport code at
all. The official Cornerstone3D React templates are roughly three majors behind.

---

## `dicom_viewer` — native Cornerstone3D viewport

### Loading data

Either give it a DICOMweb triple and let it fetch the series metadata:

```python
dicom_viewer(
    wado_rs_root="https://pacs.example.com/dicom-web",
    study_instance_uid=State.study_uid,
    series_instance_uid=State.series_uid,
    headers={"Authorization": f"Bearer {State.token}"},
)
```

…or build the `wadors:` / `wadouri:` imageIds yourself and pass them, when Python
needs to decide exactly which frames are shown:

```python
from reflex_ohif_viewer import DicomWebClient

client = DicomWebClient("https://pacs.example.com/dicom-web")
ids = client.image_ids(study_uid, series_uid)

dicom_viewer(image_ids=ids[::2])  # every other slice
```

### Rendering modes

* `mode="stack"` — 2D, frame by frame. The default, and the right choice for
  anything that is not a consistently spaced volume.
* `mode="volume"` with `orientation="axial" | "sagittal" | "coronal"` — a
  reformatted plane through a loaded volume.
* `mode="volume3d"` with a `preset` such as `"CT-Bone"` — volume rendering.

### Multi-viewport layouts

Each viewport needs its own `viewport_id`. Two ids control how viewports relate:

* the same **`tool_group_id`** makes them one group, which is what linked tools
  such as `Crosshairs` and `ReferenceLines` require;
* the same **`volume_id`** makes them share one decoded volume instead of
  loading the series once per viewport.

That is the whole MPR pattern:

```python
TOOL_GROUP = "mpr-tools"
VOLUME = "cornerstoneStreamingImageVolume:mpr"

rx.hstack(
    *[
        dicom_viewer(
            wado_rs_root=State.root,
            study_instance_uid=State.study_uid,
            series_instance_uid=State.series_uid,
            viewport_id=f"mpr-{orientation}",
            tool_group_id=TOOL_GROUP,
            volume_id=VOLUME,
            mode="volume",
            orientation=orientation,
            tools=["WindowLevel", "Pan", "Zoom", "Crosshairs", "Length"],
        )
        for orientation in ("axial", "sagittal", "coronal")
    ]
)
```

### Tools

37 tools are supported; see `ALL_TOOLS`, or the grouped
`NAVIGATION_TOOLS`, `ANNOTATION_TOOLS`, `OVERLAY_TOOLS` and
`SEGMENTATION_TOOLS`. `tools=` chooses which are registered; `active_tool=`
chooses which one holds the primary mouse button. A tool name that does not
exist raises at component-creation time rather than warning in the console.

The other bindings are fixed, matching Cornerstone's own convention: right-drag
zooms, middle-drag and Ctrl+drag pan, the wheel and Alt+drag scroll, and Escape
cancels a half-drawn annotation.

### Events

| Event | Payload |
|---|---|
| `on_viewer_ready` | `viewportId`, `toolGroupId`, `numImages`, `index`, `mode`, plus patient/study/series strings from the DICOM metadata |
| `on_slice_change` | `{"index": int, "total": int}` |
| `on_voi_change` | `{"windowWidth": float, "windowCenter": float}` |
| `on_measurements_change` | The full annotation list, each with `uid`, `toolName`, `label` and `stats` |
| `on_annotation_added` / `_modified` / `_removed` | `{"uid", "toolName"}` |
| `on_load_progress` | `{"loaded": int, "total": int}` — chatty, wire it up only for a progress bar |
| `on_error` | The error message |

### Driving the viewport from Python

Every mounted viewport registers an imperative API. The helpers return Reflex
event specs, so they work anywhere an event handler does:

```python
from reflex_ohif_viewer import (
    clear_measurements,
    jump_to_slice,
    reset_camera,
    set_tool,
    set_window_preset,
    play_cine,
)

rx.button("Lung window", on_click=set_window_preset("main", "CT Lung"))
rx.button("Measure", on_click=set_tool("main", "Length"))
rx.button("First slice", on_click=jump_to_slice("main", 0))
rx.button("Play", on_click=play_cine("main", frames_per_second=15))
rx.button("Clear", on_click=clear_measurements("main"))
```

Also available: `reset_properties`, `scroll`, `set_window`, `set_colormap`,
`set_zoom`, `rotate`, `flip`, `stop_cine`, `remove_measurement`, and
`viewer_call(viewport_id, method, *args)` for anything not wrapped.

---

## `ohif_viewer` — embedded OHIF Viewer

### Run a build

```bash
docker run -d --name ohif -p 3001:80 ohif/app:v3.13.8
```

Pin the tag. The `:latest` Docker tag and the `latest` npm dist-tag both lag the
real stable release. The official image sets no `X-Frame-Options`, so it embeds
fine. Do **not** point the component at `viewer.ohif.org`: that deployment sets
`X-Frame-Options: DENY`.

```python
ohif_viewer(
    base_url="http://localhost:3001",
    study_instance_uids=[State.study_uid],
    hanging_protocol_id="mpr",
    height="80vh",
    on_viewer_load=State.handle_loaded,
)
```

### The URL it builds

The route shape, from `platform/app/src/routes/buildModeRoutes.tsx`, is
`{base}/{modeRouteName}[/{dataSourceName}]?{query}`. The mode segment is a
mode's `routeName`, not its package id — the plain "basic viewer" is `/viewer`,
from `@ohif/mode-longitudinal`, and there is no `/basic-viewer` route.

`build_ohif_url` is the same builder as a plain function, so you can compute,
log and unit-test a link without a browser:

```python
from reflex_ohif_viewer import build_ohif_url

build_ohif_url(
    "http://localhost:3001",
    study_instance_uids=["1.2.3", "4.5.6"],  # current study plus a prior
    hanging_protocol_id="mpr",
)
# http://localhost:3001/viewer?StudyInstanceUIDs=1.2.3&StudyInstanceUIDs=4.5.6&hangingProtocolId=mpr
```

Supported parameters: `mode`, `data_source`, `study_instance_uids`,
`series_instance_uids` (a hard filter), `initial_series_instance_uid` and
`initial_sop_instance_uid` (soft — load everything, start here),
`hanging_protocol_id`, `stage_id`, `token`, `config_url`, `customization`,
`theme`, `debug`, `use_next_viewports`, `viewport_rendering`, `extra_params`,
and with `study_list=True` the worklist filters in `worklist_filters`.

See `OHIF_MODES` and `OHIF_HANGING_PROTOCOLS` for the registered values.

### Serving it under a sub-path

Serving the build at `/ohif` needs both halves, and they are spelled
differently on purpose:

* build-time `PUBLIC_URL=/ohif/` — with a trailing slash;
* runtime `routerBasename: '/ohif'` — without one.

Any static host must also rewrite unknown paths to `index.html`, or a direct
load of `/viewer?StudyInstanceUIDs=…` returns 404.

### Configuring it

`OhifAppConfig` builds OHIF's `window.config` three ways:

```python
from reflex_ohif_viewer import DicomWebDataSource, OhifAppConfig, docker_run_command

config = OhifAppConfig(
    data_sources=[
        DicomWebDataSource(
            source_name="pacs",
            qido_root="https://pacs.example.com/dicom-web",
            wado_root="https://pacs.example.com/dicom-web",
            request_options={"auth": "user:password"},
        )
    ],
)

config.to_app_config_js()  # JavaScript, for APP_CONFIG / app-config.js
config.to_json()  # JSON, to serve behind ?configUrl=
config.to_dict()  # the plain mapping

print(docker_run_command(config, port=3001))
```

The official image writes the `APP_CONFIG` environment variable over
`app-config.js` at container start, so the configuration applies without
rebuilding the bundle.

For per-session configuration, enable `dangerously_use_dynamic_config` in the
build and serve the JSON from a Reflex API route:

```python
app = rx.App()


@app.api.get("/ohif-config.json")
async def ohif_config():
    return build_config(current_session_token()).to_dict()


ohif_viewer(
    base_url="http://localhost:3001",
    config_url="http://localhost:3000/ohif-config.json",
    study_instance_uids=[State.study_uid],
)
```

Note that OHIF replaces `window.config` wholesale with the fetched document, so
it must be pure JSON — the function-valued fields (`httpErrorHandler`,
`whiteLabeling.createLogoComponentFn`, `requestOptions.auth` as a function)
cannot be delivered this way.

### What it cannot do

There is no way to read the current slice, the active measurement or the window
level out of the iframe, and no way to command it other than by changing the
URL. If you need that, the options are:

1. use `dicom_viewer` instead;
2. serve OHIF same-origin and reach `iframe.contentWindow.commandsManager`
   yourself — private API, unstable across minor versions;
3. ship your own OHIF extension that posts messages to the parent. The
   `on_viewer_message` event is already wired for it and filtered by origin.

---

## `DicomWebClient` — querying DICOMweb from Python

A study browser should be ordinary Reflex state, not something hidden inside the
viewer, so the package ships a small QIDO-RS / WADO-RS client:

```python
from reflex_ohif_viewer import DicomWebClient

client = DicomWebClient("https://pacs.example.com/dicom-web", headers={"Authorization": "Bearer …"})

studies = client.search_studies(patient_name="SMITH*", modalities_in_study="CT")
series = client.search_series(studies[0].study_instance_uid)
frames = client.image_ids(studies[0].study_instance_uid, series[0].series_instance_uid)
```

It uses `httpx`, which Reflex already depends on, and returns dataclasses that
drop straight into state fields.

---

## `CornerstonePlugin` — making the bundle work

Cornerstone3D decodes frames in web workers with four WebAssembly codecs, and
its dependency tree mixes ES modules with a few CommonJS packages. Vite needs
telling about both. Register the plugin in `rxconfig.py`:

```python
from reflex_ohif_viewer import CornerstonePlugin

config = rx.Config(
    app_name="my_app",
    plugins=[CornerstonePlugin()],
)
```

It patches `vite.config.js` to keep the Cornerstone packages out of dependency
pre-bundling — a pre-bundled chunk evaluates as a unit, so a Node-only module
Cornerstone only reaches down an unused code path (`dcmjs` → `xmlbuilder2` →
Node's `events`) would still run at import time — while forcing the small
CommonJS leaves through it, which is what gives them ES-module interop. It also
declares a browser implementation of `events`, treats `.wasm` as an asset, emits
workers as ES modules, and copies the codec `.wasm` files into `public/cs-wasm/`.

The two failures it prevents, so you recognise them if you hit them elsewhere:

* `does not provide an export named 'default'` — a CommonJS package was served
  raw. It belongs in `optimizeDeps.include`.
* `WebAssembly.instantiate(): expected magic word 00 61 73 6d, found 3c 21 64 6f`
  — the bundler served `index.html` where a `.wasm` was expected (`3c 21 64 6f`
  is `<!do`). Pass `wasm_base_path="/cs-wasm/"` to `dicom_viewer`.

---

## Public test data

`PUBLIC_DICOMWEB_ROOT` is `https://d14fa38qiwhyfd.cloudfront.net/dicomweb`, the
static DICOMweb server behind viewer.ohif.org and the Cornerstone3D examples.
`DEMO_STUDIES` holds four studies on it, with their series UIDs verified against
the live server:

| Slug | Content |
|---|---|
| `chest-ct` | PET/CT — the Cornerstone3D reference study (CT 135, PET AC/NAC 135) |
| `pet-ct` | Whole-body PET/CT — 311-slice CT, PET AC and PET NAC |
| `abdomen-ct` | Abdomen/lung CT — five reconstructions of one acquisition |
| `rtstruct` | PET/CT with RTSTRUCT contours |

It is a static DICOMweb bucket, so pointing OHIF at it needs
`static_wado=True`, `qido_supports_include_field=False` and
`supports_fuzzy_matching=False` — which is what
`DicomWebDataSource.public_demo()` sets.

---

## The demo app

```bash
cd ohif_viewer_demo
pip install -r requirements.txt
reflex run
```

Five pages: an overview, the native viewport with a full toolbar and a live
measurement table, an MPR layout, the OHIF iframe with a URL builder, and a
configuration generator that emits `app-config.js` and a `docker run` line.

Point it at your own PACS without editing anything:

```bash
OHIF_DEMO_DICOMWEB_ROOT=https://pacs.internal/dicom-web \
OHIF_DEMO_STUDY_UID=1.2.840.… \
reflex run
```

---

## Versions

Written and verified against Cornerstone3D **5.10.6**, OHIF Viewer **3.13.8**,
Reflex **0.9.11** and Python 3.10+. `VERSIONS` carries these at runtime.

## Contributing

Set-up, the checks CI runs, the branching model and how a release is cut are in
[CONTRIBUTING.md](CONTRIBUTING.md). Pull requests go to `develop`.

## Security

How to report a vulnerability, and what is and is not in scope, are in
[SECURITY.md](SECURITY.md). Two things in this API are credential-adjacent and
worth reading about before you deploy: `ohif_viewer(token=...)`, which puts a
bearer token in a URL, and the `headers` argument shared by `dicom_viewer` and
`DicomWebClient`.

## Licence

MIT. OHIF Viewer and Cornerstone3D are MIT-licensed projects of the Open Health
Imaging Foundation; this package wraps them and is not affiliated with them.

## Not a medical device

This is developer tooling. Neither this package nor the upstream projects it
wraps are cleared or certified for diagnostic use. Do not use it to make
clinical decisions.
