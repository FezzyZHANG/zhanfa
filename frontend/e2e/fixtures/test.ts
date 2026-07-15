import { expect, test as base } from '@playwright/test';

export const test = base.extend<{ browserDiagnostics: void }>({
  browserDiagnostics: [
    async ({ page }, use) => {
      const failures: string[] = [];
      page.on('console', (message) => {
        if (message.type() === 'error') failures.push(`console: ${message.text()}`);
      });
      page.on('pageerror', (error) => failures.push(`pageerror: ${error.message}`));
      page.on('response', (response) => {
        if (response.url().includes('/api/') && response.status() >= 500) {
          failures.push(`api ${response.status()}: ${response.url()}`);
        }
      });
      page.on('request', (request) => {
        const url = new URL(request.url());
        if (!['127.0.0.1', 'localhost'].includes(url.hostname)) {
          failures.push(`external request blocked by test contract: ${request.url()}`);
        }
      });

      await use();
      expect(failures, failures.join('\n')).toEqual([]);
    },
    { auto: true },
  ],
});

export { expect };
