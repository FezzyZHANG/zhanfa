import { expect, test } from '../fixtures/test';

test('data lifecycle persists through the real API @smoke @scenario', async ({ page }) => {
  const initialStats = page.waitForResponse(
    (response) => new URL(response.url()).pathname === '/api/data/stats' && response.ok(),
  );
  await page.goto('/data');
  expect(await (await initialStats).json()).toMatchObject({
    cache: { stock_count: 0, total_rows: 0 },
    database: { stock_count: 0 },
  });
  await expect(page.getByRole('heading', { name: '数据管理' })).toBeVisible();
  await expect(page.getByText('尚未初始化数据')).toBeVisible();

  const initialized = page.waitForResponse(
    (response) => new URL(response.url()).pathname === '/api/data/initialize'
      && response.request().method() === 'POST'
      && response.ok(),
  );
  await page.getByRole('button', { name: '开始初始化数据' }).click();
  expect(await (await initialized).json()).toMatchObject({
    stock_count: 1,
    message: '已导入 1 只股票到 stocks 表',
  });
  await expect(page.getByText('已导入 1 只股票到 stocks 表')).toBeVisible();
  await expect(page.getByText('股票 1')).toBeVisible();

  await page.getByRole('button', { name: '抓取至今' }).click();
  const forceRefresh = page.getByRole('checkbox', { name: /强制全量刷新/ });
  await forceRefresh.check();
  await expect(page.getByText(/从当前配置的数据源重新拉取/)).toBeVisible();
  await forceRefresh.uncheck();

  const refreshed = page.waitForResponse(
    (response) => new URL(response.url()).pathname === '/api/data/refresh'
      && response.request().method() === 'POST'
      && response.ok(),
  );
  await page.getByRole('button', { name: '开始刷新' }).click();
  expect(await (await refreshed).json()).toMatchObject({
    updated: 1,
    failed: 0,
    new_discovered: 1,
    deferred: 0,
    providers: { '600519': 'fixture' },
  });
  await expect(page.getByText('更新成功')).toBeVisible();
  await expect(page.getByText(/覆盖率 100\.0% · 4 行/)).toBeVisible();

  await page.getByRole('button', { name: '关闭' }).click();
  const reloadedStats = page.waitForResponse(
    (response) => new URL(response.url()).pathname === '/api/data/stats' && response.ok(),
  );
  await page.reload();
  expect(await (await reloadedStats).json()).toMatchObject({
    cache: { stock_count: 1, total_rows: 4, freq_stats: { daily: 1, meta: 1 } },
    database: { stock_count: 1 },
  });
  await expect(page.getByText(/覆盖率 100\.0% · 4 行/)).toBeVisible();
});
