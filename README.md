# gallery_organizer

Local photo and video organizer built with Python and Streamlit.

The project indexes a local media folder, stores metadata in SQLite, and exposes a dashboard for review, search and cleanup. It experiments with local AI models for object detection, face grouping and semantic search, but the results still need human review.

## What it does

- scans a local media folder
- extracts dates from EXIF data, filenames and folder structure
- stores file metadata in SQLite
- groups faces and detections for manual review
- provides a Streamlit interface for triage, search and cleanup

## Limits

- AI models can be wrong and should not be treated as final decisions.
- Performance depends on the local machine and gallery size.
- The app is designed for one local user, not for a shared production service.
- Some features require local ONNX models in `models/onnx/`.

## Local setup

```bash
pip install -r requirements.txt
streamlit run smart_gallery_v2/app.py
```

Before indexing a real gallery, review the paths in `smart_gallery_v2/core/config.py`.

## Tests

```bash
pytest
```

## Social preview

GitHub social preview asset: `docs/images/social-preview.png`

## Documentation

- DeepWiki: https://deepwiki.com/eneekoruiz/gallery_organizer
