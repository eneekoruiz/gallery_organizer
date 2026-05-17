

class ReviewDecider:
    @staticmethod
    def decide(
        face_confidences: list[float],
        date_confidence: str,
        quality_score: float = 1.0,
        has_unknown_person: bool = False,
        has_multiple_people: bool = False,
        has_low_face_confidence: bool = False,
        has_date_uncertain: bool = False,
        has_folder_date_conflict: bool = False,
        has_duplicate_conflict: bool = False,
        has_ai_disagreement: bool = False,
    ) -> tuple[bool, list[str], float]:
        """Determina si un archivo requiere revisión manual, listando las razones y calculando un score de confianza.

        Retorna:
            (review_required: bool, reasons: list[str], confidence_score: float)
        """
        reasons = []
        confidence_score = 1.0

        # 1. Comprobar baja confianza de caras
        if has_low_face_confidence or any(conf < 0.85 for conf in face_confidences):
            reasons.append("low_face_confidence")
            confidence_score -= 0.3

        # 2. Comprobar persona desconocida
        if has_unknown_person:
            reasons.append("unknown_person")
            confidence_score -= 0.3

        # 3. Comprobar múltiples personas
        if has_multiple_people or len(face_confidences) > 1:
            reasons.append("multiple_people")
            confidence_score -= 0.1

        # 4. Comprobar fecha incierta
        if has_date_uncertain or date_confidence in ("low", "unknown"):
            reasons.append("date_uncertain")
            confidence_score -= 0.3

        # 5. Comprobar conflicto de fecha de carpeta/EXIF/nombre
        if has_folder_date_conflict:
            reasons.append("folder_date_conflict")
            confidence_score -= 0.4

        # 6. Comprobar conflicto de duplicado
        if has_duplicate_conflict:
            reasons.append("duplicate_conflict")
            confidence_score -= 0.5

        # 7. Comprobar discrepancia de la IA (tags/caras/OCR)
        if has_ai_disagreement:
            reasons.append("ai_disagreement")
            confidence_score -= 0.3

        # 8. Comprobar calidad de imagen extremadamente baja
        if quality_score < 0.25:
            reasons.append("low_quality")
            confidence_score -= 0.4

        # Limitar score de confianza
        confidence_score = max(0.0, min(1.0, round(confidence_score, 2)))

        # Se requiere revisión si hay al menos una razón crítica o si el score es inferior a 0.85
        # NOTA: multiple_people es informativa, por sí sola no fuerza review si la confianza general es excelente (>0.85)
        critical_reasons = [r for r in reasons if r != "multiple_people"]
        review_required = len(critical_reasons) > 0 or confidence_score < 0.85

        return review_required, reasons, confidence_score
