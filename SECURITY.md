# Security policy

## Supported versions

`reflex-ohif-viewer` is pre-1.0. Only the latest released version on PyPI
receives security fixes.

| Version | Supported |
|---|---|
| 0.1.x | ✅ |
| < 0.1 | ❌ |

## Reporting a vulnerability

Report privately through GitHub's
[security advisory form](https://github.com/ecrespo/reflex-ohif-viewer/security/advisories/new).
Please do not open a public issue for a vulnerability.

Include the version, a description of the impact, and the smallest reproduction
you can manage. You should get an acknowledgement within 7 days and an
assessment within 30.

## What is and is not in scope

This package renders medical images. It is a viewer component, not a PACS and
not a data store: it holds no credentials of its own and persists nothing.

**In scope**

- Injection through the component API — anything that turns a prop, a UID or a
  DICOMweb response into executed script.
- The generated OHIF URL leaking a credential somewhere it should not go.
- The `postMessage` listener in `ohif_viewer` accepting a message from an
  origin other than the embedded viewer's.
- The Vite plugin writing outside the app's `.web/` directory.

**Out of scope**

- Vulnerabilities in the OHIF Viewer build you host. Report those to
  [OHIF](https://github.com/OHIF/Viewers/security).
- Vulnerabilities in Cornerstone3D. Report those to
  [cornerstonejs](https://github.com/cornerstonejs/cornerstone3D/security).
- Your DICOMweb server's authentication, authorisation or network exposure.
- The demo app under `ohif_viewer_demo/`, which points at public test data and
  is not published to PyPI.

## Notes for deployers

Two things in the API are credential-adjacent and deliberately explicit:

- **`ohif_viewer(token=...)`** puts a bearer token in a URL. OHIF strips it from
  the address bar after reading it, but it has still passed through browser
  history, any proxy in between and the referrer of any subresource. Prefer OIDC
  or a same-origin authenticating proxy for anything that matters.
- **`dicom_viewer(headers=...)`** and **`DicomWebClient(headers=...)`** send
  whatever you give them to the DICOMweb root you name, and to that root only.
  Do not point them at a host you do not control while carrying a token for a
  different one.

`DicomWebClient(verify=False)` disables TLS verification. It exists for a PACS
on a trusted network with a self-signed certificate, and for nothing else.

## Not a medical device

This software is not a medical device and is not cleared or approved by any
regulator for diagnostic use. See the note at the end of the README.
