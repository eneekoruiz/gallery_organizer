# Project Structure

This repository has one runnable Streamlit app package plus root-level operational files.

Layout:

- smart_gallery_v2/app.py: Streamlit entry point and page composition
- smart_gallery_v2/application/: use cases and ports; no Streamlit or SQL details
- smart_gallery_v2/core/: legacy processing facade, worker, DB, migrations, engines
- smart_gallery_v2/domain/: pure models and domain concepts
- smart_gallery_v2/infrastructure/: SQLite and filesystem adapters for newer boundaries
- smart_gallery_v2/presentation/: controller/view-model glue without Streamlit widgets
- smart_gallery_v2/tools/: maintenance and upgrade helpers
- smart_gallery_v2/ui/: Streamlit tabs and render-only code
- tests/: pytest regression suite
- docs/: durable project documentation assets
- tasks/: Windows maintenance/task scheduler scripts
- pyproject.toml: canonical test/lint/type configuration
- requirements.txt: canonical runtime/dev dependency list

## Boundaries

- ui renders state and calls application/database methods. It must not open raw SQLite connections or mutate queue columns directly.
- application orchestrates workflows through protocols from application/ports.py.
- core/database.py remains the compatibility facade for legacy screens while newer repositories move into infrastructure/sqlite.
- core/worker.py adapts heavy AI engines and delegates workflow order to application/media_pipeline.py.
- tests should cover every queue-state transition and every human correction path that can modify identities.

## Queue invariants

- Only PENDING files can be prioritized for normal background processing.
- Manual processing moves any non-PROCESSING, non-IGNORED row into PROCESSING through DatabaseManager.prepare_manual_processing.
- Completion, retry and failure transitions clear transient queue fields: priority, current_stage, failed_stage and error_message.
- The worker consumes PENDING rows ordered by priority DESC, id ASC.

## Canonical commands

pip install -r requirements.txt
pytest
streamlit run smart_gallery_v2/app.py

