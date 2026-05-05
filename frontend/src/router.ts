import { createRootRoute, createRoute, createRouter } from '@tanstack/react-router';
import { Layout } from '@/components/Layout';
import { StrategiesPage } from '@/pages/strategies/StrategiesPage';
import { StrategyDetailPage } from '@/pages/strategies/StrategyDetailPage';
import { WatchlistPage } from '@/pages/watchlist/WatchlistPage';
import { StockDetailPage } from '@/pages/stock/StockDetailPage';
import { BacktestPage } from '@/pages/backtest/BacktestPage';
import { BacktestDetailPage } from '@/pages/backtest/BacktestDetailPage';
import { DocsPage } from '@/pages/docs/DocsPage';
import { DataPage } from '@/pages/DataPage';

const rootRoute = createRootRoute({
  component: Layout,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/',
  component: StrategiesPage,
});

const strategiesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/strategies',
  component: StrategiesPage,
});

const strategyDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/strategies/$strategyId',
  component: StrategyDetailPage,
});

export interface WatchlistSearchParams {
  sortKey?: string;
  sortDir?: string;
  search?: string;
  peMin?: string;
  peMax?: string;
  changeDir?: string;
}

export interface DocsSearchParams {
  file?: string;
}

const watchlistRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/watchlist',
  validateSearch: (search: Record<string, unknown>): WatchlistSearchParams => ({
    sortKey: typeof search.sortKey === 'string' ? search.sortKey : 'code',
    sortDir: typeof search.sortDir === 'string' ? search.sortDir : 'asc',
    search: typeof search.search === 'string' ? search.search : '',
    peMin: typeof search.peMin === 'string' ? search.peMin : '',
    peMax: typeof search.peMax === 'string' ? search.peMax : '',
    changeDir: typeof search.changeDir === 'string' ? search.changeDir : '',
  }),
  component: WatchlistPage,
});

const stockDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/stock/$stockCode',
  component: StockDetailPage,
});

const backtestRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/backtest',
  component: BacktestPage,
});

const backtestDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/backtest/$backtestId',
  component: BacktestDetailPage,
});

const dataRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/data',
  component: DataPage,
});

const docsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: '/docs',
  validateSearch: (search: Record<string, unknown>): DocsSearchParams => (
    typeof search.file === 'string' ? { file: search.file } : {}
  ),
  component: DocsPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  strategiesRoute,
  strategyDetailRoute,
  watchlistRoute,
  stockDetailRoute,
  backtestRoute,
  backtestDetailRoute,
  dataRoute,
  docsRoute,
]);

export const router = createRouter({ routeTree });

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router;
  }
}
