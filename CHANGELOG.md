# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[semantic versioning](https://semver.org/).

## [0.1.0] — 2026-09-17

First release.

### Added

- **`ohif_viewer`** — embeds a self-hosted OHIF Viewer v3 build in an iframe,
  with every viewer and study-list query parameter exposed as a prop:
  studies and priors, series filters, initial series and instance, hanging
  protocol and stage, token, `configUrl`, customization, theme, debug and the
  `multimonitor` / `screenNumber` pair.
  Events: `on_viewer_load`, `on_url_change`, `on_viewer_message`.
- **`build_ohif_url`** — the same URL builder as a plain function, so links can
  be computed, logged and unit-tested server-side. The Python and JavaScript
  implementations are pinned to each other by a parity test that runs the
  JavaScript one under Node.
- **`dicom_viewer`** — a native Cornerstone3D 5.10.6 viewport: stack, volume
  (MPR) and 3D volume rendering; 37 tools; window/level, colormap, inversion and
  cine driven from props; a four-corner DICOM overlay; and a DICOMweb loader
  that builds `wadors:` imageIds and caches series metadata. Events report the
  viewer's readiness, slice, window/level, annotations and errors back to Reflex
  state.
- **Imperative API** — `set_tool`, `jump_to_slice`, `scroll`, `set_window`,
  `set_window_preset`, `set_colormap`, `set_zoom`, `rotate`, `flip`,
  `reset_camera`, `reset_properties`, `play_cine`, `stop_cine`,
  `clear_measurements`, `remove_measurement` and the general `viewer_call`.
- **`DicomWebClient`** — QIDO-RS study, series and instance search plus WADO-RS
  metadata, so a study browser can be ordinary Reflex state.
- **`OhifAppConfig` / `DicomWebDataSource`** — build OHIF's `window.config` as
  JavaScript (for `APP_CONFIG` / `app-config.js`), as JSON (for `?configUrl=`)
  or as a plain mapping, plus `docker_run_command` for a ready-to-run container.
- **`CornerstonePlugin`** — configures Vite for Cornerstone: keeps the
  Cornerstone packages out of dependency pre-bundling, forces the CommonJS
  leaves through it, declares a browser `events` implementation, treats `.wasm`
  as an asset, emits ES-module workers, and copies the codec `.wasm` files into
  `public/cs-wasm/`.
- **Constants** — grouped tool lists, window presets, colormaps, volume-
  rendering presets, OHIF modes and hanging protocol ids, and four public demo
  studies whose series UIDs were verified against the live server.
- **A five-page demo app** — overview, native viewport with a live measurement
  table, MPR, the OHIF iframe with a URL builder, and a configuration generator.

### Project

- **Continuous integration** — `ci.yml` runs ruff, checks that the generated
  `.pyi` stubs still match the component source, runs the suite on Python 3.10
  to 3.13 with Node present so the URL-builder parity test does not skip, and
  builds the distribution, installs the wheel into a clean environment and
  imports it to prove the frontend assets are really packaged.
- **Security validation** — `security.yml` runs Bandit over the published
  package, `pip-audit` over the installed dependency tree, Gitleaks over the
  full history, and a dependency review on every pull request; `codeql.yml`
  analyses both the Python and the JavaScript halves. The two scheduled runs
  catch advisories published against code that has not changed.
- **Release automation** — `release.yml` is triggered by a `vX.Y.Z` tag. It
  refuses to run unless the tag, `pyproject.toml` and this changelog agree,
  re-runs the checks against the tagged commit, then publishes to PyPI through
  Trusted Publishing (OpenID Connect — the repository holds no PyPI token) with
  build attestations, and opens a GitHub Release carrying that version's
  changelog section.
- **Packaging** — the licence is declared as a PEP 639 SPDX expression rather
  than the deprecated classifier, and `MANIFEST.in` puts the changelog, the
  security policy and the contributing guide into the sdist.

### Security notes

- `viewer_call` validates its `method` argument as a JavaScript identifier. The
  viewport id and the arguments are JSON-encoded on their way into the generated
  script, but a method name is a property access and cannot be, so it was the
  one place a caller could have spliced script into the page.

### Notes on the upstream projects

Checked against the OHIF 3.13.8 source and the published npm tarballs rather
than the documentation:

- `@ohif/app` on npm is a prebuilt static site. Its `main` points at
  `dist/index.umd.js`, a file the tarball does not contain, so
  `import App from '@ohif/app'` has never worked. There is no web component
  either.
- OHIF defines no postMessage protocol. `ohif_viewer` therefore builds a URL and
  nothing more; `on_viewer_message` exists for deployments that add their own
  OHIF extension.
- The `:latest` Docker tag and the `latest` npm dist-tag both lag the real
  stable release — pin `ohif/app:v3.13.8`.
- `@cornerstonejs/streaming-image-volume-loader` was merged into
  `@cornerstonejs/core` in 2.x and is not installed.
- No existing React wrapper for Cornerstone3D was usable:
  `@cornerstonejs/react` and `react-cornerstone3d` do not exist on npm,
  `react-cornerstone-viewport` targets the abandoned legacy cornerstone, and
  `@ohif/ui-next` contains no viewport code.

[0.1.0]: https://github.com/ecrespo/reflex-ohif-viewer/releases/tag/v0.1.0
