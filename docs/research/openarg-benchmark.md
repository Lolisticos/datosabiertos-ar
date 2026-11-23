# Benchmark de referencia: OpenArg

Revisión realizada el 2026-11-23 sobre evidencia pública. Este documento no
reproduce código ni identidad visual; identifica decisiones útiles y diferencias
de alcance.

## Evidencia consultada

- [`colossus-lab/openarg_backend`](https://github.com/colossus-lab/openarg_backend):
  README, arquitectura y configuración pública del backend, con licencia MIT.
- [`colossus-lab/openarg_frontend`](https://github.com/colossus-lab/openarg_frontend):
  interfaz pública Next.js/React, con licencia MIT.
- [`colossus-lab/openarg-mcp`](https://github.com/colossus-lab/openarg-mcp):
  servidor MCP público del ecosistema.
- [openarg.org](https://openarg.org): producto web referenciado por los
  repositorios.

Las afirmaciones siguientes se limitan a lo observable en esas fuentes. No se
infiere la ausencia de capacidades privadas.

## Qué demuestra OpenArg

OpenArg presenta una plataforma madura orientada a preguntas en lenguaje
natural sobre datos públicos. Su backend declara FastAPI, PostgreSQL con
pgvector, Redis, Celery, S3, conectores oficiales, catálogo, marts curados,
búsqueda semántica y motores con LLM. Expone el mismo motor por web, API y MCP,
y documenta controles de cuotas, verificación de cifras, calidad y tareas
programadas. El frontend ofrece conversación, streaming y gráficos.

La referencia valida varias ideas generales: separar conectores del núcleo,
mantener catálogo y procedencia, medir frescura/calidad, curar vistas para
consultas repetibles y compartir contratos entre canales.

## Diferencias deliberadas de DatosAbiertos AR

| Tema | OpenArg observable | Decisión de esta fase |
| --- | --- | --- |
| Experiencia principal | Preguntas naturales y respuestas asistidas | Exploración directa del catálogo oficial |
| Arquitectura | Servicios, workers, Redis, pgvector, S3 y modelos | Monolito modular, PostgreSQL y filesystem RAW |
| Búsqueda | Semántica/híbrida | Texto normalizado con PostgreSQL/pg_trgm |
| Ingesta | Múltiples portales, tablas y marts | Un CKAN nacional, metadatos primero |
| IA | Parte central del producto | Fuera del núcleo y fuera de esta entrega |
| Visualización | Gráficos derivados de consultas | Solo cuando haya contenido verificable compatible |

DatosAbiertos AR toma la trazabilidad, los conectores y la calidad como
principios, pero evita adoptar la complejidad operativa o la propuesta de
producto de OpenArg antes de demostrar una necesidad propia.

