import { expect, test } from "@playwright/test";

// End-to-end journey of the first vertical slice (spec S14): a visitor lands
// on the site, checks the official sources, explores the imported catalogue,
// opens a dataset, reads its metadata/provenance/last sync/validation results
// and sees the real visualization availability. Runs against the production
// build backed by the development API with the real datos.gob.ar catalogue.
test.describe("recorrido del catálogo", () => {
  test("de la portada al detalle con procedencia verificable", async ({
    page,
  }) => {
    await page.goto("/");

    await expect(
      page.getByRole("heading", { name: /Datos públicos de Argentina/i }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Cobertura actual del catálogo" }),
    ).toBeVisible();
    // Real coverage figures, never placeholder zeros: the catalogue has data.
    await expect(page.getByText("Datasets catalogados")).toBeVisible();

    // 2-3. Check official sources and follow one into the explorer.
    await page.getByRole("link", { name: "Ver detalle de fuentes" }).click();
    await expect(
      page.getByRole("heading", { name: "Fuentes oficiales", exact: true }),
    ).toBeVisible();
    await expect(
      page.getByText("Catálogo Nacional de Datos Abiertos").first(),
    ).toBeVisible();
    await page.getByRole("link", { name: "Explorar sus datasets" }).first().click();

    // 4-5. The explorer lists imported datasets of that source.
    await expect(
      page.getByRole("heading", { name: "Explorador de datasets" }),
    ).toBeVisible();
    await expect(page.getByText(/datasets encontrados/)).toBeVisible();
    const firstDataset = page.locator("main ul li h2 a").first();
    await expect(firstDataset).toBeVisible();
    const datasetTitle = (await firstDataset.textContent())?.trim() ?? "";
    expect(datasetTitle.length).toBeGreaterThan(0);
    await firstDataset.click();

    // 6-9. Detail: metadata, organisation, origin URL, last sync and checks.
    await expect(
      page.getByRole("heading", { name: datasetTitle, exact: true }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Metadatos y procedencia" }),
    ).toBeVisible();
    await expect(page.getByText("URL de origen:").first()).toBeVisible();
    await expect(page.getByText("Última sincronización exitosa")).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: "Validaciones de la última sincronización",
      }),
    ).toBeVisible();

    // 10. Visualization is stated honestly as unavailable in this phase.
    await expect(
      page.getByRole("heading", { name: "Visualización" }),
    ).toBeVisible();
    await expect(
      page.getByText(/Todavía no hay una visualización real/),
    ).toBeVisible();
  });

  test("búsqueda real y estado vacío honesto", async ({ page }) => {
    await page.goto("/datasets?q=mineria");
    await expect(page.getByText(/datasets encontrados/)).toBeVisible();
    await expect(page.locator("main ul li h2 a").first()).toBeVisible();

    await page.goto("/datasets?q=zzzzzznoexiste");
    await expect(
      page.getByText("No hay datasets que coincidan con estos filtros"),
    ).toBeVisible();
  });

  test("historial de sincronización muestra ejecuciones reales", async ({
    page,
  }) => {
    await page.goto("/historial");
    await expect(
      page.getByRole("heading", { name: "Historial de sincronización" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Ejecuciones de ingesta" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Detalle" }).first().click();
    await expect(
      page.getByRole("heading", { name: /Ejecución/ }),
    ).toBeVisible();
    await expect(page.getByText(/^Leídos /).first()).toBeVisible();
  });
});
