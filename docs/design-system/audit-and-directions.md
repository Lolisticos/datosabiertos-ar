# DatosAbiertos AR — Auditoría y direcciones visuales

Estado: **Review**  
Versión de exploración: **0.1.0**  
Ruta comparativa: `/design-directions`

Este documento registra la auditoría del producto existente y las reglas que
condicionan la selección de una dirección visual. Todavía no constituye el
Design System oficial v1.0.0.

## Evidencia revisada

- Portada, catálogo, detalle, indicadores, dashboard EMAE, fuentes, historial y
  páginas informativas.
- Componentes de navegación, estados, métricas, gráficos, tablas y procedencia.
- Configuración ECharts de la serie temporal.
- Preview real con API no disponible.
- Fixture oficial EMAE y metadatos CKAN incluidos en el repositorio.

## Auditoría por impacto

### Alto

1. **Dependencia visual total de la API.** Cuando FastAPI no responde, la portada
   se reduce a un bloque de error. Deben preservarse contexto, navegación,
   metodología y accesos no dependientes de datos.
2. **Jerarquía estadística insuficiente.** Métrica principal, filtros, gráfico,
   tabla y procedencia compiten mediante tarjetas de peso similar.
3. **Responsive funcional pero no diseñado.** Faltan contratos específicos para
   filtros, toolbars, tablas y lectura de gráficos en 390 px.

### Medio

1. La escala tipográfica surge de decisiones locales y no de estilos nombrados.
2. Catálogo, dashboard y contenido editorial comparten una densidad demasiado
   similar.
3. El gráfico EMAE resuelve correctamente datos ausentes, SVG, `aria` y reduced
   motion, pero no comparte un theme de ECharts gobernado por tokens.
4. Los filtros son accesibles y enlazables, pero no jerarquizan búsqueda,
   facetas, conteos y filtros activos.
5. La repetición de radios, bordes y superficies hace que la interfaz pierda
   contraste jerárquico.

### Fortalezas

1. Geist, formato `es-AR`, tono sobrio y paleta cívica coherente.
2. No se fabrican valores ni se convierten ausencias en cero.
3. Skip link, landmarks, encabezados, foco visible, tablas equivalentes y
   preferencia de movimiento reducido.
4. Procedencia, hashes, transformación y fuente son parte del producto.
5. Los filtros via URL y la renderización de servidor favorecen accesibilidad,
   enlace permanente y trazabilidad.

## Direcciones

### A — Data Editorial

- Jerarquía basada en título, dato, explicación, visualización y evidencia.
- Menos superficies cerradas y más separación mediante ritmo, tipografía y
  reglas.
- Gráficos amplios y acompañados por una lectura editorial breve.
- Densidad media para ciudadanía y consulta ocasional.

### B — Civic Intelligence

- Métricas, filtros, calidad y tabla visibles de manera simultánea.
- Paneles compactos y mayor densidad para exploración recurrente.
- Búsqueda global y estados operativos persistentes.
- Mantiene tono institucional sin adoptar sidebar ni patrones de backoffice.

## Recomendación

Adoptar **Data Editorial** como lenguaje principal e incorporar de Civic
Intelligence únicamente:

- densidad compacta para exploradores, historial y tablas;
- filtros laterales en desktop;
- estado y calidad persistentes;
- composición gráfico + tabla para investigación.

Esto crea una identidad única con modos de densidad, en lugar de dos sistemas
paralelos.

## Gobernanza preliminar

### Capas de tokens

1. `primitive`: escalas cromáticas, medidas y valores puros.
2. `semantic`: intención de interfaz y datos.
3. `component`: decisiones excepcionales y estables de un componente.

Ejemplos:

```text
color.teal.700
color.neutral.950
color.text.primary
color.surface.default
color.chart.series.1
space.4
radius.md
component.metricCard.padding.standard
```

Los componentes aprobados no consumen valores HEX directos.

### Tipografía

Geist es la única familia base. La escala propuesta es:

```text
Display
Heading XL / L / M / S
Body L / M / S
Label
Caption
Overline
Data XL / L / M
```

Los estilos `Data` requieren números tabulares. Precisión, redondeo y unidad
dependen del contrato del indicador, no del componente.

### Espaciado y grillas

- Base 4 px: `space.1`, `2`, `3`, `4`, `5`, `6`, `8`, `10`, `12`, `16`.
- Desktop: 12 columnas.
- Tablet: 8 columnas.
- Mobile: 4 columnas.
- Contenedor editorial: 960 px.
- Contenedor de aplicación: 1280 px.

### Temas y series

- Un color temático identifica dominio, nunca disponibilidad o calidad.
- La identidad global permanece teal + neutros.
- Paleta categórica de hasta ocho series.
- Para series adicionales se combinan color, trazo, símbolo y etiqueta directa.
- Datos ausentes, referencias y bandas de incertidumbre tienen tokens propios.

### Contrato de gráficos

```text
Chart Container
├── Chart Header
│   ├── Title
│   ├── Description
│   └── Controls
├── Chart Canvas
├── Legend
├── Data Notes
└── Source Attribution
```

Variantes: `compact`, `standard`, `expanded`, `comparison`.

- Barras parten de cero salvo justificación documentada.
- Líneas pueden usar escala no cero si el rango queda visible.
- Valores ausentes interrumpen la serie.
- Tooltip: período, indicador, valor, unidad y fuente cuando corresponda.
- ECharts debe consumir un theme compartido generado desde tokens.

### Componentes y estados

Propiedades semánticas:

```text
density: compact | standard | comfortable
emphasis: primary | secondary | quiet
state: default | loading | empty | error | unavailable
size: sm | md | lg
```

Estados interactivos obligatorios cuando correspondan: default, hover, focus,
active, selected, disabled, loading, error y empty.

### Correspondencia Figma–código

| Figma | CSS/Tailwind |
| --- | --- |
| `color/text/primary` | `--color-text-primary` |
| `color/chart/series/1` | `--color-chart-series-1` |
| `space/4` | `--space-4` |
| `radius/md` | `--radius-md` |
| `Data/XL` | utilidad o clase tipográfica compartida |

No se permiten aliases locales con nombre de pantalla.

### Aprobación y versionado

- Estados: Draft → Review → Approved → Deprecated.
- Revisión obligatoria: diseño, contenido, accesibilidad y frontend.
- Solo `Approved` puede utilizarse en producción.
- SemVer: `1.0.0` inicial; minor para adiciones compatibles; patch para
  correcciones; major para cambios incompatibles.

### Excepciones

Cada excepción registra:

1. componente y regla afectada;
2. justificación;
3. alcance;
4. responsable;
5. fecha de revisión o caducidad;
6. impacto de accesibilidad.

Una excepción no crea automáticamente un nuevo patrón.
