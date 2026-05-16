from core.status import QueueStatus


class ReviewDecider:
    @staticmethod
    def decide(
        face_confidences: list[float],
        date_confidence: str,
        quality_score: float = 1.0,
    ) -> QueueStatus:
        """Determina el estado final en la cola de procesamiento (AUTO_CLASSIFIED o NEEDS_REVIEW).

        - NEEDS_REVIEW si hay caras con confianza media/baja (< 0.85).
        - NEEDS_REVIEW si la confianza de la fecha es 'low' (filesystem/folder).
        - NEEDS_REVIEW si la calidad de imagen es extremadamente baja (< 0.25).
        - AUTO_CLASSIFIED en cualquier otro caso.
        """
        # Si hay caras detectadas, verificar que todas tengan alta confianza
        for conf in face_confidences:
            if conf < 0.85:
                return QueueStatus.NEEDS_REVIEW

        # Confianza de fecha baja requiere revisión
        if date_confidence == "low":
            return QueueStatus.NEEDS_REVIEW

        # Mala calidad de imagen
        if quality_score < 0.25:
            return QueueStatus.NEEDS_REVIEW

        return QueueStatus.AUTO_CLASSIFIED
