# reflex-ohif-viewer demo

```bash
pip install -r requirements.txt
reflex run
```

Then open http://localhost:3000.

## Pages

| Route | What it shows |
|---|---|
| `/` | The two components side by side, and what the research into OHIF turned up |
| `/native` | The Cornerstone3D viewport with a full toolbar, window presets, a slice slider and a live measurement table — all Reflex state |
| `/mpr` | Three orthographic viewports over one volume, sharing a tool group and a volume id |
| `/ohif` | The OHIF iframe, with the generated URL shown as you change the controls |
| `/deploy` | A form that emits `app-config.js` and a `docker run` line |

## Pointing it at your own data

The demo defaults to the public OHIF DICOMweb server. Two environment
variables override that without editing any code:

```bash
OHIF_DEMO_DICOMWEB_ROOT=https://pacs.internal/dicom-web \
OHIF_DEMO_STUDY_UID=1.2.840.113619.2.290.3.3767434740.226.1600859119.501 \
reflex run
```

## The OHIF iframe page needs a running OHIF build

```bash
docker run -d --name ohif -p 3001:80 ohif/app:v3.13.8
```

Then put `http://localhost:3001` in the base URL field. Pin the tag: the
`:latest` tag lags the real stable release.
