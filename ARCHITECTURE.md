# Arquitectura objetivo

La aplicación adopta una arquitectura hexagonal incremental. Streamlit queda en
`ui/`; los casos de uso en `application/`; las reglas y value objects en
`domain/`; SQLite, filesystem y motores externos en `infrastructure/` y `core/`.
El código legacy permanece detrás de adaptadores mientras se migra sin romper
galerías existentes.

```text
smart_gallery_v2/
├── app.py                         # composición y navegación lazy
├── domain/                        # modelos inmutables, sin frameworks
├── application/                   # casos de uso y puertos (Protocols)
├── infrastructure/
│   ├── sqlite/                    # repositorios, una transacción por caso de uso
│   └── filesystem/                # integración con el SO
├── presentation/                  # view models/controladores sin Streamlit
├── ui/                            # renderizado; sin SQL ni operaciones del SO
├── core/
│   ├── migrations/                # migraciones idempotentes y versionadas
│   ├── event_engine.py            # agrupamiento tiempo/GPS/semántica
│   ├── worker.py                  # adaptador de motores pesados
│   └── database.py                # fachada legacy de compatibilidad
└── tools/apply_upgrade.py         # backup + todas las migraciones
```

## Flujos principales

1. `MediaPipeline` orquesta estabilidad, EXIF/GPS, deduplicación, IA,
   materialización y persistencia con una frontera única de errores.
2. Una corrección humana crea `RegionAnnotations` + `IdentityEvidence`; nunca
   destruye la inferencia original. `ResolvedIdentityPresence` aplica precedencia
   humana y `TrainingExamples` conserva casos para Active Learning.
3. `EventEngine` segmenta cronológicamente, exige proximidad geográfica cuando
   ambos elementos tienen GPS y usa similitud semántica cuando no lo tienen.
4. Los cambios de filesystem se registran en `FilesystemOutbox`, evitando
   confirmar datos y fallar después al crear una proyección.

## Invariantes

- Coordenadas de regiones normalizadas en `[0, 1]`.
- Latitud/longitud validadas por value objects.
- Evidencia humana con confianza 1 y prioridad sobre modelos.
- Migraciones idempotentes, registradas en `AppSchemaMigrations`.
- Una sola página Streamlit se renderiza por rerun.
- La UI no contiene SQL ni llamadas directas al sistema operativo en los flujos
  nuevos.

## Estrategia de retirada legacy

`DatabaseManager`, `KnownFaces`, `Detections` y `FileIdentities` son una capa de
compatibilidad. Las escrituras nuevas mantienen una proyección legacy para que
las pantallas antiguas sigan funcionando. Cuando todas consuman repositorios,
se podrá eliminar esa proyección en una migración mayor, después de comparar
conteos y exportar un backup.
