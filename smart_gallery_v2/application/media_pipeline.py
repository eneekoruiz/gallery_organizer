"""Orquestación del procesamiento; no conoce Streamlit, OpenCV ni SQL."""

from __future__ import annotations

import logging

from application.ports import JobRepository, PipelineSteps

from core.models_types import ExifResult, MediaRecord, ProcessResult

log = logging.getLogger(__name__)


class MediaPipeline:
    def __init__(self, steps: PipelineSteps, jobs: JobRepository) -> None:
        self._steps = steps
        self._jobs = jobs

    def execute(self, record: MediaRecord) -> ProcessResult:
        stage = "stability"
        try:
            self._jobs.update_stage(record.id, stage)
            if not self._steps.check_stability(record.filepath):
                return self._fail(record.id, stage, "Archivo inestable o no encontrado")

            stage = "thumbnail"
            self._jobs.update_stage(record.id, stage)
            thumbnail = self._steps.thumbnail(record.filepath)
            if thumbnail.error:
                log.warning("Thumbnail fallido para %s: %s", record.filepath, thumbnail.error)

            exif = ExifResult()
            if record.media_type == "image":
                stage = "exif"
                self._jobs.update_stage(record.id, stage)
                exif = self._steps.exif(record.filepath)

                stage = "dedupe"
                self._jobs.update_stage(record.id, stage)
                duplicate = self._steps.dedupe(record.filepath, record.id)
                if duplicate.is_duplicate:
                    self._steps.persist_duplicate(record, duplicate, thumbnail.thumb_path)
                    self._jobs.update_stage(record.id, "completed")
                    return ProcessResult(record.id, "DONE", stage, "Duplicado vinculado")

            stage = "ai"
            self._jobs.update_stage(record.id, stage)
            ai = self._steps.ai(record.filepath, record.id, record.media_type)
            if ai.error:
                return self._fail(record.id, stage, ai.error)

            stage = "materialize"
            self._jobs.update_stage(record.id, stage)
            self._steps.materialize_results(record, ai)
            stage = "persist"
            self._jobs.update_stage(record.id, stage)
            self._steps.persist(record, ai, exif, thumbnail.thumb_path)
            self._jobs.update_stage(record.id, "completed")
            return ProcessResult(record.id, "DONE", stage, "Procesado correctamente")
        except Exception as exc:
            log.exception("Pipeline fallido en %s para %s", stage, record.filepath)
            return self._fail(record.id, stage, str(exc), exception=str(exc))

    def _fail(
        self, file_id: int, stage: str, message: str, exception: str | None = None
    ) -> ProcessResult:
        self._jobs.update_error(file_id, stage=stage, message=message)
        return ProcessResult(file_id, "ERROR", stage, message, exception=exception)
