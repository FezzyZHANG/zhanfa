import { expect, test } from '../fixtures/test';

test('data stats survive a reload through the real API @smoke', async ({ page }) => {
  let statsResponses = 0;
  page.on('response', (response) => {
    if (new URL(response.url()).pathname === '/api/data/stats') statsResponses += 1;
  });

  const firstStats = page.waitForResponse(
    (response) => new URL(response.url()).pathname === '/api/data/stats' && response.ok(),
  );
  await page.goto('/data');
  const firstResponse = await firstStats;
  expect(await firstResponse.json()).toMatchObject({
    cache: { stock_count: 1, total_rows: 3 },
    database: { stock_count: 1 },
  });
  await expect(page.getByRole('heading', { name: '数据管理' })).toBeVisible();
  await expect(page.getByText(/覆盖率 100\.0% · 3 行/)).toBeVisible();
  await expect(page.getByText('股票 1')).toBeVisible();

  const reloadedStats = page.waitForResponse(
    (response) => new URL(response.url()).pathname === '/api/data/stats' && response.ok(),
  );
  await page.reload();
  await reloadedStats;
  await expect(page.getByText(/覆盖率 100\.0% · 3 行/)).toBeVisible();
  expect(statsResponses).toBeGreaterThanOrEqual(2);
});
