import type { Metadata, Viewport } from "next";
import { GeistSans } from "geist/font/sans";
import "./globals.css";
import { SiteHeader } from "@/components/site-header";
import { SiteFooter } from "@/components/site-footer";

export const metadata: Metadata = {
  title: {
    default: "DatosAbiertos AR — Datos públicos de Argentina",
    template: "%s | DatosAbiertos AR",
  },
  description:
    "Explorá el catálogo de fuentes oficiales argentinas con procedencia verificable: fuentes, datasets, historial de sincronización y resultados de validación.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es-AR">
      <body className={`${GeistSans.className} flex min-h-screen flex-col antialiased`}>
        <a
          href="#contenido"
          className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-accent focus:px-4 focus:py-2 focus:text-white"
        >
          Saltar al contenido
        </a>
        <SiteHeader />
        <main id="contenido" className="mx-auto w-full max-w-7xl flex-1 px-4 py-7 sm:px-6 lg:px-8">
          {children}
        </main>
        <SiteFooter />
      </body>
    </html>
  );
}
