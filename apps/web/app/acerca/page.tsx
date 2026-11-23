import { Breadcrumbs } from "@/components/navigation/breadcrumbs";

export const metadata = { title: "Acerca del proyecto" };

export default function AboutPage() {
  return (
    <article className="max-w-4xl">
      <Breadcrumbs items={[{ label: "Inicio", href: "/" }, { label: "Acerca" }]} />
      <h1 className="text-3xl font-semibold tracking-tight">Acerca de DatosAbiertos AR</h1>
      <p className="mt-4 text-lg leading-8 text-muted">Una plataforma independiente para descubrir, comparar y verificar datos públicos oficiales de Argentina.</p>
      <div className="mt-8 space-y-7 text-ink">
        <section>
          <h2 className="text-xl font-semibold">Cómo tratamos los datos</h2>
          <p className="mt-2 leading-7 text-muted">Cada descarga se conserva como RAW con su hash. Las reglas de normalización tienen versión y las observaciones publicadas mantienen el vínculo con el snapshot y la transformación que las produjo.</p>
        </section>
        <section>
          <h2 className="text-xl font-semibold">Qué no hacemos</h2>
          <p className="mt-2 leading-7 text-muted">No completamos valores faltantes, no representamos ausencia como cero y no mezclamos series incompatibles. Cuando una fuente falla, la interfaz lo informa sin inventar cifras.</p>
        </section>
        <section>
          <h2 className="text-xl font-semibold">Acceso técnico</h2>
          <p className="mt-2 leading-7 text-muted">El catálogo, el historial y los indicadores se exponen mediante una API REST versionada. Cada dashboard ofrece además una tabla accesible y descarga CSV.</p>
        </section>
      </div>
    </article>
  );
}
