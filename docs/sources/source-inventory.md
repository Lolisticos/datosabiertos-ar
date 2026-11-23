# Inventario inicial de fuentes oficiales

Observación realizada el 2026-11-23. Los conteos son una fotografía del momento,
no una garantía contractual. “Integrable” describe la viabilidad técnica
observada desde este entorno.

| Fuente / organismo | Jurisdicción | URL y acceso | Formatos / catálogo | Licencia y actualización observable | Identificadores, restricciones y calidad | Integración |
| --- | --- | --- | --- | --- | --- | --- |
| Catálogo Nacional de Datos Abiertos | Nación | [datos.gob.ar](https://datos.gob.ar) · CKAN `api/3/action` | 1.293 datasets; recursos CSV, XLSX, JSON, ZIP y otros | Licencia por dataset/recurso; ejemplos CC BY 4.0; fechas CKAN por registro | UUID CKAN, organismos y temas; algunos recursos sin URL; respuestas grandes pueden truncarse | **Implementada**, metadata-only |
| Datos Abiertos PBA | Provincia de Buenos Aires | [catalogo.datos.gba.gob.ar](https://catalogo.datos.gba.gob.ar) · CKAN | 105 datasets observados | Metadatos/licencia por paquete; frecuencia variable | Identificadores CKAN; revisar términos y estabilidad por recurso | Candidata |
| Datos Abiertos Mendoza | Mendoza | [datosabiertos.mendoza.gov.ar](https://datosabiertos.mendoza.gov.ar) · CKAN | 204 datasets observados | Metadatos por paquete; frecuencia variable | Identificadores CKAN; calidad heterogénea | Candidata |
| Buenos Aires Data | Ciudad Autónoma de Buenos Aires | [data.buenosaires.gob.ar](https://data.buenosaires.gob.ar) · API de catálogo | 463 datasets observados | Términos y fechas por dataset | Requiere adaptar el contrato al portal y validar formatos | Candidata |
| API Series de Tiempo | Nación / organismos productores | [apis.datos.gob.ar/series](https://apis.datos.gob.ar/series/) · HTTP JSON | Series económicas y sociales; JSON/CSV | Metadatos con frecuencia y fuente; actualización según serie | Identificador de serie; valores y unidades requieren validación semántica | Candidata para indicadores |
| Portal Santa Fe | Santa Fe | [datos.santafe.gob.ar](https://datos.santafe.gob.ar) | No verificado como CKAN desde este entorno | No determinada | Servidor respondió con protocolo HTTP antiguo | Requiere reevaluación |
| Datos Rosario | Rosario | [datos.rosario.gob.ar](https://datos.rosario.gob.ar) | No recuperado durante la prueba | No determinada | Timeout de conexión | Requiere reevaluación |

## Fuente elegida

El catálogo nacional fue priorizado por cobertura, API CKAN documentada,
identificadores estables y metadatos de licencia/procedencia. La sincronización
usa `sort=name asc`, páginas de 50 con reducción automática y deduplicación
defensiva. Las URLs de recursos no se descargan por solicitud anónima: solo los
conectores autorizados pueden acceder a ellas y deben aplicar la política SSRF.

