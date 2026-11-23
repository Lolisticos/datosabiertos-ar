// Footer states the freshness contract: figures come from the API at request
// time and trace back to official sources.
export function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-line bg-white">
      <div className="mx-auto max-w-6xl px-4 py-6 text-sm text-muted">
        <p className="font-semibold text-ink">DatosAbiertos AR</p>
        <p className="mt-1 max-w-3xl">
          Plataforma de datos públicos de Argentina. Toda cifra publicada aquí
          se obtiene de la API en el momento de la consulta y puede rastrearse
          hasta el artefacto original descargado de la fuente oficial. Esta
          fase expone metadatos de catálogo; no publica indicadores propios.
        </p>
      </div>
    </footer>
  );
}
