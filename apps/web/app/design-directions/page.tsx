import type { ReactNode } from "react";
import styles from "./design-directions.module.css";

export const metadata = {
  title: "Laboratorio de dirección visual",
  description:
    "Auditoría y comparación de las direcciones Data Editorial y Civic Intelligence.",
};

const audit = [
  {
    impact: "Fortaleza",
    tone: "strong",
    title: "Base cívica honesta",
    text: "La paleta sobria, Geist, el formato es-AR y la decisión de no fabricar datos ya construyen confianza. La trazabilidad no es decorativa: está presente en tablas, estados y procedencia.",
  },
  {
    impact: "Alto",
    tone: "high",
    title: "La API domina toda la experiencia",
    text: "Cuando FastAPI no está disponible, la portada se reduce a un único bloque de error. Falta una degradación que preserve navegación, contexto, metodología y accesos no dependientes de datos.",
  },
  {
    impact: "Alto",
    tone: "high",
    title: "Jerarquía estadística débil",
    text: "Métricas, gráficos, filtros y procedencia usan superficies visualmente similares. El dato principal no siempre supera en jerarquía al contenedor que lo rodea.",
  },
  {
    impact: "Medio",
    tone: "medium",
    title: "Escala tipográfica sin contrato",
    text: "Las decisiones son razonables pero locales: abundan text-sm, text-xs y títulos puntuales. Falta una escala nombrada para titulares editoriales, datos, labels y notas.",
  },
  {
    impact: "Medio",
    tone: "medium",
    title: "Densidad poco diferenciada",
    text: "Catálogo, dashboard y páginas explicativas comparten tarjetas, radios y paddings similares. El explorador técnico necesita mayor densidad que la portada sin convertirse en un panel administrativo.",
  },
  {
    impact: "Medio",
    tone: "medium",
    title: "Gráfico correcto, contrato incompleto",
    text: "ECharts usa SVG, datos ausentes como cortes, aria y movimiento reducido. Faltan tokens compartidos de ejes, grilla, tooltip, series, alturas y estados de comparación.",
  },
  {
    impact: "Medio",
    tone: "medium",
    title: "Filtros eficaces pero planos",
    text: "Los filtros son accesibles y compartibles por URL, pero no comunican bien filtros activos, conteos, jerarquía entre búsqueda y facetas ni comportamiento móvil.",
  },
  {
    impact: "Fortaleza",
    tone: "strong",
    title: "Accesibilidad estructural sólida",
    text: "Hay skip link, landmarks, encabezados, tablas equivalentes, foco visible, objetivos de 44 px en gráficos y reduced motion. Debe sumarse contraste documentado y navegación de series por teclado.",
  },
  {
    impact: "Alto",
    tone: "high",
    title: "Responsive funcional, no diseñado",
    text: "Las grillas colapsan y la navegación desplaza horizontalmente, pero faltan patrones deliberados para tablas, toolbars, filtros persistentes y lectura de gráficos en 390 px.",
  },
];

const comparison = [
  ["Jerarquía", "Narrativa, dato y fuente en secuencia", "Estado, filtros y comparación simultáneos"],
  ["Densidad", "Media, con respiración editorial", "Alta, organizada en paneles compactos"],
  ["Navegación", "Pocas decisiones, lectura progresiva", "Accesos rápidos y herramientas visibles"],
  ["Gráficos", "Amplios, explicados y protagonistas", "Integrados con métricas, tabla y calidad"],
  ["Ciudadanía", "Más directa para público general", "Más potente para usuarios recurrentes"],
  ["Implementación", "Menor complejidad de componentes", "Mayor disciplina de estados y responsive"],
];

const datasets = [
  {
    title: "Índice de producción minero (IPIM)",
    org: "Secretaría de Minería",
    description:
      "Series del índice de producción minero del SIACAM, en base a datos de INDEC.",
    meta: ["4 recursos", "CSV", "Economía y Finanzas"],
  },
  {
    title: "Anuncios de Inversión en el Sector Minero de Argentina",
    org: "Secretaría de Minería",
    description:
      "Anuncios de inversión del SIACAM elaborados por la Subsecretaría de Desarrollo Minero.",
    meta: ["1 recurso", "CSV", "CC BY 4.0"],
  },
  {
    title: "Estimador Mensual de Actividad Económica (EMAE). Base 2004",
    org: "Instituto Nacional de Estadística y Censos",
    description:
      "Índice original mensual del EMAE publicado como serie oficial verificable.",
    meta: ["Serie mensual", "JSON / CSV", "Índice 2004=100"],
  },
];

function BrowserFrame({
  path,
  children,
}: {
  path: string;
  children: ReactNode;
}) {
  return (
    <div className={styles.browser}>
      <div className={styles.browserBar} aria-hidden="true">
        <i />
        <i />
        <i />
        <span>datosabiertos.ar{path}</span>
      </div>
      {children}
    </div>
  );
}

function Brand() {
  return (
    <div className={styles.protoBrand}>
      <span className={styles.brandMark} aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      <span>DatosAbiertos AR</span>
    </div>
  );
}

function PrototypeHeader({ active }: { active: string }) {
  const items = ["Inicio", "Indicadores", "Datos y fuentes", "Actualizaciones"];
  return (
    <div className={styles.protoHeader}>
      <Brand />
      <div className={styles.protoNav}>
        {items.map((item) =>
          item === active ? <b key={item}>{item}</b> : <span key={item}>{item}</span>,
        )}
      </div>
    </div>
  );
}

function EmaeChart({ compact = false }: { compact?: boolean }) {
  return (
    <svg
      className={styles.chart}
      viewBox={compact ? "0 0 460 190" : "0 0 620 190"}
      role="img"
      aria-label="Muestra EMAE de enero a marzo de 2025: 146,50 en enero, sin dato en febrero y 150,61 en marzo."
    >
      <line className={styles.chartGrid} x1="44" y1="28" x2={compact ? "440" : "600"} y2="28" />
      <line className={styles.chartGrid} x1="44" y1="84" x2={compact ? "440" : "600"} y2="84" />
      <line className={styles.chartGrid} x1="44" y1="140" x2={compact ? "440" : "600"} y2="140" />
      <text x="5" y="32">152</text>
      <text x="5" y="88">148</text>
      <text x="5" y="144">144</text>
      <path className={styles.chartLine} d={compact ? "M 70 105" : "M 80 105"} />
      <circle className={styles.chartDot} cx={compact ? "70" : "80"} cy="105" r="5" />
      <circle className={`${styles.chartDot} ${styles.missingDot}`} cx={compact ? "250" : "320"} cy="151" r="5" />
      <circle className={styles.chartDot} cx={compact ? "420" : "570"} cy="48" r="5" />
      <text x={compact ? "48" : "56"} y="174">Ene 2025</text>
      <text x={compact ? "226" : "294"} y="174">Feb 2025</text>
      <text x={compact ? "396" : "544"} y="174">Mar 2025</text>
      <text x={compact ? "225" : "292"} y="139">Sin dato</text>
    </svg>
  );
}

function EditorialHome() {
  return (
    <BrowserFrame path="/">
      <div className={`${styles.prototype} ${styles.a}`}>
        <PrototypeHeader active="Inicio" />
        <div className={styles.aBody}>
          <section className={styles.aHero}>
            <div>
              <p className={styles.aEyebrow}>Datos públicos de Argentina</p>
              <h4>Información oficial para comprender el país</h4>
              <p>
                Indicadores, fuentes y datasets con metodología visible y trazabilidad
                hasta el recurso original.
              </p>
              <div className={styles.aSearch}>
                <span>Buscar por tema, territorio u organismo</span>
                <b>Buscar</b>
              </div>
            </div>
          </section>
          <div className={styles.aStats}>
            <div className={styles.aStat}><strong>1.293</strong><span>datasets catalogados</span></div>
            <div className={styles.aStat}><strong>7.694</strong><span>recursos oficiales</span></div>
            <div className={styles.aStat}><strong>42</strong><span>snapshots RAW preservados</span></div>
          </div>
          <div className={styles.aSectionTitle}>
            <h5>Qué podés explorar</h5>
            <span>Ver todos los indicadores</span>
          </div>
          <div className={styles.editorialList}>
            <div className={styles.editorialRow}>
              <span>Economía</span>
              <div><h6>Actividad económica</h6><p>EMAE original mensual, con serie, tabla y procedencia.</p></div>
              <b>150,61</b>
            </div>
            <div className={styles.editorialRow}>
              <span>Fuentes</span>
              <div><h6>Catálogo Nacional de Datos Abiertos</h6><p>Metadatos oficiales publicados mediante CKAN.</p></div>
              <b>1.293 datasets</b>
            </div>
            <div className={styles.editorialRow}>
              <span>Calidad</span>
              <div><h6>Datos verificables, ausencias visibles</h6><p>Un valor faltante nunca se representa como cero.</p></div>
              <b>Ver método</b>
            </div>
          </div>
        </div>
      </div>
    </BrowserFrame>
  );
}

function EditorialDashboard() {
  return (
    <BrowserFrame path="/temas/economia/actividad">
      <div className={`${styles.prototype} ${styles.a}`}>
        <PrototypeHeader active="Indicadores" />
        <div className={styles.aBody}>
          <div className={styles.aDashboardTop}>
            <div>
              <p className={styles.aEyebrow}>Economía · Serie oficial</p>
              <h4 className={styles.aPageTitle}>Actividad económica</h4>
              <p className={styles.aIntro}>
                Evolución mensual del EMAE. Serie original del INDEC, índice base
                2004=100.
              </p>
            </div>
            <div className={styles.aMetricLead}>
              <strong>150,61</strong>
              <span>Marzo de 2025<br />Índice 2004=100</span>
            </div>
          </div>
          <section className={styles.chartEditorial}>
            <div className={styles.chartMeta}>
              <div><h5>EMAE — serie original</h5><p>Muestra verificable disponible en el repositorio</p></div>
              <span>3 períodos · 1 sin dato</span>
            </div>
            <EmaeChart />
          </section>
          <div className={styles.aNotes}>
            <p><b>Lectura.</b> Febrero no tiene valor publicado en la muestra y se presenta como interrupción.</p>
            <p><b>Fuente.</b> INDEC vía API de Series de Tiempo de datos.gob.ar.</p>
          </div>
          <div className={styles.aSectionTitle}>
            <h5>Metodología y procedencia</h5>
            <span>Descargar CSV</span>
          </div>
          <div className={styles.editorialList}>
            <div className={styles.editorialRow}><span>Unidad</span><div><h6>Índice 2004=100</h6><p>Frecuencia mensual · serie original.</p></div><b>Oficial</b></div>
            <div className={styles.editorialRow}><span>Fuente</span><div><h6>Instituto Nacional de Estadística y Censos</h6><p>Recurso y transformación versionados.</p></div><b>Ver origen</b></div>
          </div>
        </div>
      </div>
    </BrowserFrame>
  );
}

function EditorialExplorer() {
  return (
    <BrowserFrame path="/datasets">
      <div className={`${styles.prototype} ${styles.a}`}>
        <PrototypeHeader active="Datos y fuentes" />
        <div className={styles.aBody}>
          <p className={styles.aEyebrow}>Catálogo técnico</p>
          <h4 className={styles.aPageTitle}>Explorar datasets</h4>
          <p className={styles.aIntro}>
            Metadatos oficiales normalizados, con actualización, licencia y procedencia.
          </p>
          <div className={styles.aFilterBar}>
            <div className={styles.field}><small>Buscar</small><span>Producción, educación, territorio…</span></div>
            <div className={styles.field}><small>Organismo</small><span>Todos</span></div>
            <div className={styles.field}><small>Formato</small><span>Todos</span></div>
          </div>
          <div className={styles.aSectionTitle}><h5>1.293 resultados</h5><span>2 filtros activos</span></div>
          <div className={styles.editorialList}>
            {datasets.map((dataset) => (
              <article className={styles.datasetEditorial} key={dataset.title}>
                <div>
                  <h6>{dataset.title}</h6>
                  <p>{dataset.org} · {dataset.description}</p>
                  <dl>{dataset.meta.map((item) => <span key={item}>{item}</span>)}</dl>
                </div>
                <span>Disponible</span>
              </article>
            ))}
          </div>
        </div>
      </div>
    </BrowserFrame>
  );
}

function IntelligenceHome() {
  return (
    <BrowserFrame path="/">
      <div className={`${styles.prototype} ${styles.b}`}>
        <PrototypeHeader active="Inicio" />
        <div className={styles.bBody}>
          <div className={styles.bCommand}><span>Buscar datasets, indicadores u organismos</span><b>Buscar</b></div>
          <div className={styles.bHero}>
            <section className={styles.panel}>
              <p className={styles.bEyebrow}>Panorama de datos públicos</p>
              <h4>Información oficial para investigar y comparar</h4>
              <p>Acceso integrado a indicadores, metadatos y evidencia de actualización.</p>
              <div className={styles.bSearch}><span>Ej.: actividad económica</span><b>Explorar</b></div>
            </section>
            <aside className={styles.panel}>
              <div className={styles.bSectionLabel}><h5>Cobertura</h5><span>Actualizada</span></div>
              <div className={styles.coverageList}>
                <div className={styles.coverageItem}><span>Datasets</span><strong>1.293</strong></div>
                <div className={styles.coverageItem}><span>Recursos</span><strong>7.694</strong></div>
                <div className={styles.coverageItem}><span>Organismos</span><strong>38</strong></div>
                <div className={styles.coverageItem}><span>Temas</span><strong>13</strong></div>
              </div>
            </aside>
          </div>
          <div className={styles.bMetricGrid}>
            <div className={styles.bMetric}><span>EMAE · Mar 2025</span><strong>150,61</strong></div>
            <div className={styles.bMetric}><span>Snapshots RAW</span><strong>42</strong></div>
            <div className={styles.bMetric}><span>Fuente integrada</span><strong>1</strong></div>
            <div className={styles.bMetric}><span>Última sync</span><strong>14 s</strong></div>
          </div>
          <div className={styles.bGrid}>
            <section className={styles.panel}>
              <div className={styles.bSectionLabel}><h5>Accesos destacados</h5><span>Ver catálogo</span></div>
              <div className={styles.compactRows}>
                <div className={styles.compactRow}><span>Economía</span><div><h6>Actividad económica</h6><p>EMAE original · INDEC</p></div><b>150,61</b></div>
                <div className={styles.compactRow}><span>Catálogo</span><div><h6>Índice de producción minero</h6><p>4 recursos CSV</p></div><b>Disponible</b></div>
                <div className={styles.compactRow}><span>Fuentes</span><div><h6>datos.gob.ar</h6><p>CKAN nacional</p></div><b>1.293</b></div>
              </div>
            </section>
            <aside className={styles.panel}>
              <div className={styles.bSectionLabel}><h5>Actividad reciente</h5><span>Historial</span></div>
              <ul className={styles.activityFeed}>
                <li><i /><span>Sincronización completa y verificada.</span></li>
                <li><i /><span>42 snapshots RAW preservados.</span></li>
                <li><i /><span>Ausencias publicadas sin imputación.</span></li>
              </ul>
            </aside>
          </div>
        </div>
      </div>
    </BrowserFrame>
  );
}

function IntelligenceDashboard() {
  return (
    <BrowserFrame path="/temas/economia/actividad">
      <div className={`${styles.prototype} ${styles.b}`}>
        <PrototypeHeader active="Indicadores" />
        <div className={styles.bBody}>
          <div className={styles.bDashboardHead}>
            <div>
              <p className={styles.bEyebrow}>Economía / Actividad</p>
              <h4 className={styles.bPageTitle}>EMAE · Serie original</h4>
              <p className={styles.bIntro}>Índice base 2004=100 · Frecuencia mensual · Fuente INDEC</p>
            </div>
            <div className={styles.segmented}><span>5 años</span><span>10 años</span><b>Todo</b></div>
          </div>
          <div className={styles.bMetricGrid}>
            <div className={styles.bMetric}><span>Último valor</span><strong>150,61</strong></div>
            <div className={styles.bMetric}><span>Período</span><strong>Mar 2025</strong></div>
            <div className={styles.bMetric}><span>Observaciones</span><strong>3</strong></div>
            <div className={styles.bMetric}><span>Sin dato</span><strong>1</strong></div>
          </div>
          <div className={styles.bGrid}>
            <section className={styles.panel}>
              <div className={styles.bSectionLabel}><h5>Evolución mensual</h5><span>Descargar · Ampliar</span></div>
              <EmaeChart compact />
              <div className={styles.quality}>Serie oficial · Ausencias visibles · Datos no imputados</div>
            </section>
            <aside className={styles.panel}>
              <div className={styles.bSectionLabel}><h5>Observaciones</h5><span>CSV</span></div>
              <table className={styles.bTable}>
                <thead><tr><th>Período</th><th>Valor</th></tr></thead>
                <tbody>
                  <tr><td>Mar 2025</td><td>150,61</td></tr>
                  <tr><td>Feb 2025</td><td>Sin dato</td></tr>
                  <tr><td>Ene 2025</td><td>146,50</td></tr>
                </tbody>
              </table>
              <div className={styles.quality}>Cobertura: Ene–Mar 2025</div>
            </aside>
          </div>
          <section className={`${styles.panel}`} style={{ marginTop: "0.7rem" }}>
            <div className={styles.bSectionLabel}><h5>Fuente y metodología</h5><span>Ver evidencia</span></div>
            <div className={styles.compactRows}>
              <div className={styles.compactRow}><span>Fuente</span><div><h6>INDEC</h6><p>API de Series de Tiempo</p></div><b>Oficial</b></div>
              <div className={styles.compactRow}><span>Unidad</span><div><h6>Índice 2004=100</h6><p>Serie original mensual</p></div><b>Verificada</b></div>
            </div>
          </section>
        </div>
      </div>
    </BrowserFrame>
  );
}

function IntelligenceExplorer() {
  return (
    <BrowserFrame path="/datasets">
      <div className={`${styles.prototype} ${styles.b}`}>
        <PrototypeHeader active="Datos y fuentes" />
        <div className={styles.bBody}>
          <div className={styles.bDashboardHead}>
            <div><p className={styles.bEyebrow}>Explorador técnico</p><h4 className={styles.bPageTitle}>Catálogo de datasets</h4><p className={styles.bIntro}>1.293 resultados · metadatos oficiales normalizados</p></div>
            <div className={styles.segmented}><b>Lista</b><span>Fuentes</span></div>
          </div>
          <div className={styles.bCommand} style={{ marginTop: "0.8rem" }}><span>Buscar por tema, territorio u organismo</span><b>Buscar</b></div>
          <div className={styles.bFilters}>
            <aside className={styles.filterPanel}>
              <h5>Filtrar resultados</h5>
              <div className={styles.filterOption}><span>Disponibles</span><b>1.293</b></div>
              <div className={styles.filterOption}><span>Economía</span><b>421</b></div>
              <div className={styles.filterOption}><span>CSV</span><b>—</b></div>
              <div className={styles.filterOption}><span>Secretaría de Minería</span><b>—</b></div>
            </aside>
            <section className={styles.resultPanel}>
              {datasets.map((dataset) => (
                <article className={styles.resultCard} key={dataset.title}>
                  <div className={styles.resultTop}>
                    <div><h6>{dataset.title}</h6><p>{dataset.org}<br />{dataset.description}</p></div>
                    <span className={styles.available}>Disponible</span>
                  </div>
                  <div className={styles.resultMeta}>{dataset.meta.map((item) => <span key={item}>{item}</span>)}</div>
                </article>
              ))}
            </section>
          </div>
        </div>
      </div>
    </BrowserFrame>
  );
}

function Direction({
  id,
  label,
  title,
  description,
  principles,
  children,
}: {
  id: string;
  label: string;
  title: string;
  description: string;
  principles: string[];
  children: ReactNode;
}) {
  return (
    <section id={id} className={styles.section}>
      <div className={styles.directionHeader}>
        <div>
          <p className={styles.kicker}>{label}</p>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <div className={styles.principles}>
          {principles.map((principle) => <span key={principle}>{principle}</span>)}
        </div>
      </div>
      <div className={styles.screenGrid}>{children}</div>
    </section>
  );
}

export default function DesignDirectionsPage() {
  return (
    <div className={styles.lab}>
      <header className={styles.intro}>
        <p className={styles.kicker}>Design System · Fase de exploración</p>
        <h1 className={styles.title}>Dos maneras de hacer legibles los datos públicos</h1>
        <p className={styles.lede}>
          Auditoría del producto actual y comparación controlada de Data Editorial y
          Civic Intelligence. Las seis pantallas usan el mismo contenido verificable;
          todavía no constituyen la biblioteca oficial.
        </p>
        <div className={styles.statusRow}>
          <span className={styles.status}>Geist</span>
          <span className={styles.status}>Tailwind CSS 4</span>
          <span className={styles.status}>ECharts 6</span>
          <span className={styles.status}>WCAG 2.2 AA como objetivo</span>
          <span className={styles.status}>Estado: Review</span>
        </div>
      </header>

      <section className={styles.section} aria-labelledby="audit-title">
        <div className={styles.sectionHead}>
          <p className={styles.kicker}>01 · Auditoría visual</p>
          <h2 id="audit-title">Una base sólida que todavía depende de decisiones locales</h2>
          <p>
            La revisión combina código, componentes existentes y preview real. Los
            hallazgos se clasifican por impacto y respetan la arquitectura y las
            funcionalidades actuales.
          </p>
        </div>
        <div className={styles.auditGrid}>
          {audit.map((item) => (
            <article className={styles.auditCard} key={item.title}>
              <span className={`${styles.impact} ${item.tone === "high" ? styles.impactHigh : item.tone === "medium" ? styles.impactMedium : styles.impactStrong}`}>
                {item.impact}
              </span>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className={styles.section} aria-labelledby="comparison-title">
        <div className={styles.sectionHead}>
          <p className={styles.kicker}>02 · Criterio de comparación</p>
          <h2 id="comparison-title">Misma información, distinta prioridad</h2>
        </div>
        <table className={styles.comparisonTable}>
          <thead><tr><th>Criterio</th><th>Data Editorial</th><th>Civic Intelligence</th></tr></thead>
          <tbody>{comparison.map(([criterion, a, b]) => <tr key={criterion}><td><b>{criterion}</b></td><td>{a}</td><td>{b}</td></tr>)}</tbody>
        </table>
      </section>

      <Direction
        id="direccion-a"
        label="Dirección A"
        title="Data Editorial"
        description="Una publicación estadística contemporánea: menos contenedores, mayor jerarquía tipográfica y una secuencia explícita entre dato, interpretación, metodología y fuente."
        principles={["Narrativa primero", "Densidad media", "Gráficos protagonistas"]}
      >
        <div className={styles.screenBlock}><h3>A1 · Portada</h3><EditorialHome /></div>
        <div className={styles.screenBlock}><h3>A2 · Dashboard EMAE</h3><EditorialDashboard /></div>
        <div className={styles.screenBlock}><h3>A3 · Explorador</h3><EditorialExplorer /></div>
      </Direction>

      <Direction
        id="direccion-b"
        label="Dirección B"
        title="Civic Intelligence"
        description="Una herramienta pública de análisis: mayor densidad, estados visibles y acceso simultáneo a métricas, filtros y evidencia, sin adoptar convenciones de panel administrativo."
        principles={["Exploración rápida", "Densidad alta", "Contexto persistente"]}
      >
        <div className={styles.screenBlock}><h3>B1 · Portada</h3><IntelligenceHome /></div>
        <div className={styles.screenBlock}><h3>B2 · Dashboard EMAE</h3><IntelligenceDashboard /></div>
        <div className={styles.screenBlock}><h3>B3 · Explorador</h3><IntelligenceExplorer /></div>
      </Direction>

      <section className={styles.section} aria-labelledby="evaluation-title">
        <div className={styles.sectionHead}>
          <p className={styles.kicker}>03 · Evaluación</p>
          <h2 id="evaluation-title">Recomendación: un sistema editorial con modos de alta densidad</h2>
        </div>
        <div className={styles.recommendation}>
          <h3>Adoptar Data Editorial como dirección base</h3>
          <p>
            Es más legible para ciudadanía, refuerza la confianza institucional y
            hace que unidad, período, fuente y metodología formen parte de la lectura.
            Para catálogo, historial y tablas se recomienda incorporar la densidad,
            los filtros laterales y los estados compactos de Civic Intelligence como
            variantes controladas, no como una segunda identidad.
          </p>
        </div>
      </section>

      <section className={styles.section} aria-labelledby="governance-title">
        <div className={styles.sectionHead}>
          <p className={styles.kicker}>04 · Gobernanza preliminar</p>
          <h2 id="governance-title">Reglas antes que pantallas aisladas</h2>
          <p>
            Esta propuesta define el contrato mínimo a aprobar antes de producir la
            biblioteca oficial v1.0.0.
          </p>
        </div>
        <div className={styles.governanceGrid}>
          <article className={styles.governanceCard}><h3>Tokens</h3><ul><li>Primitivos: color.teal.50–900, neutral.0–950, violet, status y chart.</li><li>Semánticos: background, surface, text, border, action, feedback y data.</li><li>Ningún componente aprobado consume HEX directo.</li></ul></article>
          <article className={styles.governanceCard}><h3>Tipografía</h3><ul><li>Geist: Display, Heading XL/L/M/S, Body L/M/S, Label, Caption y Overline.</li><li>Data XL/L/M usa números tabulares y precisión declarada por indicador.</li><li>Escala fluida solo en Display y Heading XL.</li></ul></article>
          <article className={styles.governanceCard}><h3>Espacio y grilla</h3><ul><li>Base 4 px: 1, 2, 3, 4, 5, 6, 8, 10, 12 y 16.</li><li>12 columnas desktop, 8 tablet, 4 mobile.</li><li>Contenedores: editorial 960 px y aplicación 1280 px.</li></ul></article>
          <article className={styles.governanceCard}><h3>Datos y temáticas</h3><ul><li>Color temático identifica dominio, nunca estado.</li><li>Hasta ocho series categóricas; luego sumar trazo y símbolo.</li><li>Ausente ≠ cero; referencia y datos faltantes tienen tokens propios.</li></ul></article>
          <article className={styles.governanceCard}><h3>Contrato de gráficos</h3><ul><li>Header, canvas, leyenda, notas y fuente.</li><li>Variantes compact, standard, expanded y comparison.</li><li>Barras desde cero; líneas pueden escalar con rango visible.</li></ul></article>
          <article className={styles.governanceCard}><h3>Componentes</h3><ul><li>Propiedades semánticas: density, emphasis, state y size.</li><li>Estados: default, hover, focus, selected, disabled, loading, error y empty.</li><li>Responsive y accesibilidad forman parte del componente.</li></ul></article>
          <article className={styles.governanceCard}><h3>Nombres y código</h3><ul><li>Figma: color/text/primary; código: --color-text-primary.</li><li>Un alias semántico por intención, no por pantalla.</li><li>ECharts consume un theme compartido generado desde tokens.</li></ul></article>
          <article className={styles.governanceCard}><h3>Aprobación</h3><ul><li>Draft → Review → Approved → Deprecated.</li><li>Revisión de diseño, contenido, accesibilidad y frontend.</li><li>Solo Approved puede aparecer en producción.</li></ul></article>
          <article className={styles.governanceCard}><h3>Versionado y excepciones</h3><ul><li>SemVer: 1.0.0 inicial, minor compatible, patch correctivo.</li><li>Excepción con regla, motivo, alcance, responsable y caducidad.</li><li>Toda excepción debe revisarse antes de crear una variante.</li></ul></article>
        </div>
      </section>
    </div>
  );
}
