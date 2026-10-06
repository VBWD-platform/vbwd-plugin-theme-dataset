/**
 * S152 walkthrough @theme_dataset — a buyer in the themed data store: the catalogue
 * index → a category → the dataset's detail page → "Get dataset" →
 * `/checkout?source=dataset` by invoice → the confirmation with the dataset line.
 *
 * Seeds (admin API, removed afterwards): a dataset category, a paid dataset in it and a
 * fresh buyer (force-deleted with the invoice it created).
 */
import { test, expect } from '@playwright/test';
import { uniqueSlug } from '@fe-user-e2e/frontend-mode/frontend-mode-support';
import {
  AdminSeeder,
  CONFIRMATION_URL_PATTERN,
  WalkthroughSteps,
  loginInBrowser,
  skipUnlessThemeMode,
  type WalkthroughBuyer,
} from '../../../theme/tests/e2e/support/walkthrough-support';

const DATASET_PRICE = 7;

test.describe('Walkthrough @theme_dataset — data store, detail, get dataset, checkout', () => {
  skipUnlessThemeMode(test);

  const steps = new WalkthroughSteps('theme_dataset');
  const datasetTitle = uniqueSlug('Walkthrough Air Quality');
  let seeder: AdminSeeder;
  let category: Record<string, any>;
  let dataset: Record<string, any>;
  let buyer: WalkthroughBuyer;

  test.beforeAll(async () => {
    seeder = await AdminSeeder.open();
    category = await seeder.create(
      '/api/v1/admin/cms/terms',
      { term_type: 'dataset_category', name: uniqueSlug('Walkthrough Environment') },
      (term) => `/api/v1/admin/cms/terms/${term.id}`,
    );
    dataset = await seeder.create(
      '/api/v1/admin/datasets',
      {
        slug: uniqueSlug('walkthrough-dataset'),
        title: datasetTitle,
        description: 'Hourly readings, seeded by the theme_dataset walkthrough.',
        source_attribution: 'S152 walkthrough',
        price: DATASET_PRICE,
        is_active: true,
      },
      (created) => `/api/v1/admin/datasets/${created.id}`,
    );
    await seeder.send('POST', `/api/v1/admin/datasets/${dataset.id}/categories`, { term_id: category.id });
    buyer = await seeder.freshBuyer();
  });

  test.afterAll(async () => {
    await seeder?.cleanup();
  });

  test('a buyer browses the data store and buys a dataset by invoice @theme_dataset', async ({ page }) => {
    await loginInBrowser(page, buyer);

    await page.goto('/data-store');
    const index = page.locator('[data-testid="dataset-catalogue-index"]');
    await expect(index).toBeVisible();
    await steps.themed(page, '01-catalogue-index');

    await index.locator(`a[href="/data-store/${category.slug}"]`).click();
    await expect(page).toHaveURL(`/data-store/${category.slug}`);
    await expect(page.locator('[data-testid="dataset-catalogue-list"]')).toBeVisible();
    await steps.themed(page, '02-category');

    await page.locator(`[data-testid="dataset-card"][href="/data-store/${category.slug}/${dataset.slug}"]`).click();
    await expect(page).toHaveURL(`/data-store/${category.slug}/${dataset.slug}`);
    await expect(page.locator('h1.dataset-detail-name')).toHaveText(datasetTitle);
    await steps.themed(page, '03-dataset-detail');

    await page.click('[data-testid="dataset-get-btn"]');
    await expect(page).toHaveURL(new RegExp(`/checkout\\?source=dataset&dataset_slug=${dataset.slug}$`));
    await expect(page.locator(`[data-testid="dataset-line-item-${dataset.id}"]`)).toContainText(datasetTitle);
    await page.fill('[data-testid="billing-first-name"]', 'Walk');
    await page.fill('[data-testid="billing-last-name"]', 'Analyst');
    await page.fill('[data-testid="billing-street"]', '3 Data Lane');
    await page.fill('[data-testid="billing-city"]', 'Munich');
    await page.fill('[data-testid="billing-zip"]', '80331');
    await page.locator('[data-testid="billing-country"]').selectOption({ index: 1 });
    await page.locator('[data-testid="payment-method-invoice"]').click();
    await page.locator('[data-testid="terms-checkbox"] input[type="checkbox"]').check();
    await expect(page.locator('[data-testid="confirm-checkout"]')).toBeEnabled();
    await steps.themed(page, '04-dataset-checkout');
    await page.click('[data-testid="confirm-checkout"]');

    await page.waitForURL(CONFIRMATION_URL_PATTERN);
    await expect(page.locator('[data-testid="confirmation-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="invoice-details"]')).toBeVisible();
    await expect(page.locator('[data-testid="line-item-row"]').first()).toContainText(datasetTitle);
    await steps.themed(page, '05-confirmation');
  });
});
