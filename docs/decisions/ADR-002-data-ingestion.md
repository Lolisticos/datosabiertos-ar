# ADR-002: ingesta, preservación y alcance de datos

- Estado: aceptado
- Fecha: 2026-11-23

## Contexto

Las fuentes públicas cambian de esquema, disponibilidad y formato. La plataforma
debe poder explicar de dónde salió cada registro, repetir transformaciones y
distinguir cambios efectivos de variaciones incidentales.

## Decisión

El primer recorrido integra el catálogo CKAN nacional `datos.gob.ar` y es
deliberadamente **metadata-only**. Se normalizan datasets, recursos, organismos,
temas, licencias y fechas, pero no se importan masivamente las tablas contenidas
en cada recurso.

Cada conector implementa `discover`, `fetch` y `metadata`. La ingesta:

1. opera únicamente sobre fuentes autorizadas en la base;
2. pagina con orden estable y deduplicación por identificador externo;
3. aplica timeout, backoff, rate limit, límites de tamaño y protección SSRF;
4. calcula hashes canónicos antes de escribir;
5. conserva el payload original en almacenamiento RAW cuando corresponde;
6. registra ejecución, versión de transformación, chequeos y cambios;
7. es idempotente ante una respuesta equivalente.

Las observaciones futuras usan `Numeric`, fechas de observación separadas de las
de descarga/proceso y dimensiones JSONB canónicas con hash, evitando una
migración por cada dataset.

## Consecuencias

El catálogo ya puede explorarse y auditarse con costos acotados. Las
visualizaciones se declaran no disponibles hasta ingerir contenido tabular real;
la interfaz no inventa indicadores. Incorporar datos de recursos requerirá una
política por formato, licencia, tamaño, frecuencia y calidad, apoyada en los
mismos artefactos RAW y contratos de procedencia.

