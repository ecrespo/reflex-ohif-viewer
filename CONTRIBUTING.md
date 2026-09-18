# Contributing

## Getting set up

```bash
git clone git@github.com:ecrespo/reflex-ohif-viewer.git
cd reflex-ohif-viewer
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

Node is optional but recommended: one test runs the JavaScript URL builder under
Node to check it against the Python one, and skips itself when Node is missing.

## The checks CI runs

Run these before opening a pull request; they are exactly what
`.github/workflows/ci.yml` and `security.yml` run.

```bash
ruff check .                              # lint
ruff format --check .                     # formatting
pytest -q                                 # tests
bandit -c pyproject.toml -r custom_components   # Python SAST
pip-audit                                 # dependency advisories
python -m build && twine check dist/*     # the artifacts PyPI will get
```

## Branching and releases

- `main` is the released branch and is protected. Nothing lands on it directly.
- `develop` is the integration branch. Open your pull request against it.
- A release is a pull request from `develop` to `main`, then a `vX.Y.Z` tag on
  `main`. The tag is what triggers `.github/workflows/release.yml`, which builds
  the artifacts, publishes them to PyPI through Trusted Publishing and opens a
  GitHub Release.

Every release needs a new version number in `pyproject.toml` — PyPI refuses to
replace a version that already exists — and a matching `CHANGELOG.md` section.
The release workflow refuses to run if the tag and `pyproject.toml` disagree.

## Publishing

Nothing in this repository holds a PyPI credential. The release workflow
authenticates to PyPI over OpenID Connect through
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/), so the
`pypi` job mints a short-lived token for one upload and there is nothing to
rotate or leak.

That needs one entry on PyPI, created once by the project owner at
<https://pypi.org/manage/account/publishing/> (for the very first release, use
the *pending publisher* form — the project does not exist on PyPI yet):

| Field | Value |
|---|---|
| PyPI Project Name | `reflex-ohif-viewer` |
| Owner | `ecrespo` |
| Repository name | `reflex-ohif-viewer` |
| Workflow name | `release.yml` |
| Environment name | `pypi` |

The `pypi` environment also has to exist in this repository, under
*Settings → Environments*. Add a required reviewer to it if you want a human to
approve every upload; the workflow will wait on it.

To cut a release:

```bash
# On develop: bump the version and write the changelog section.
$EDITOR pyproject.toml CHANGELOG.md
git commit -am "chore: release 0.2.0"
# Open and merge the pull request into main, then:
git checkout main && git pull
git tag -a v0.2.0 -m "v0.2.0"
git push origin v0.2.0
```

The tag is the trigger. The workflow re-runs the lint and tests against the
tagged commit, builds the sdist and wheel, publishes them to PyPI with build
attestations, and opens a GitHub Release whose notes are that version's
changelog section.

### Gallery listing

The [Reflex component gallery](https://reflex.dev/docs/custom-components/) is a
separate registry from PyPI, and registering is manual and done once:

```bash
reflex login
reflex component share
```

It asks for the published package name (`reflex-ohif-viewer`) and, optionally, a
preview image and a demo URL. Publish to PyPI first — `share` does not check
that the package exists.

## Working on the component

The two Python component classes have generated `.pyi` stubs next to them,
marked `DO NOT EDIT`. After adding or changing a prop, regenerate them:

```bash
python -c "from reflex.utils.pyi_generator import PyiGenerator; \
PyiGenerator().scan_all(['custom_components/reflex_ohif_viewer'])"
```

CI checks that the committed stubs match the source, so a forgotten regeneration
fails the build rather than shipping stale autocomplete.

If you touch `rxOhifUrl.js` or `build_ohif_url`, keep them in step —
`tests/test_url_builder_parity.py` runs both and compares the result.

## Trying it out

```bash
cd ohif_viewer_demo
reflex run
```

The demo defaults to the public OHIF DICOMweb server. The `/ohif` page needs a
running OHIF build:

```bash
docker run -d --name ohif -p 3001:80 ohif/app:v3.13.8
```

## Scope

This package wraps OHIF and Cornerstone3D; it does not fork them. Bugs in the
rendering itself belong upstream. What belongs here is the Reflex surface: props,
events, the URL and config builders, the DICOMweb client and the Vite plugin.
