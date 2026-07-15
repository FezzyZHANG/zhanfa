import { createServer } from 'node:net';
import { createWriteStream, mkdirSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import process from 'node:process';

const frontendRoot = path.resolve(import.meta.dirname, '../..');
const repoRoot = path.resolve(frontendRoot, '..');
const artifactsDir = path.join(frontendRoot, 'e2e-artifacts');
const logDir = path.join(artifactsDir, 'logs');

function freePort() {
  return new Promise((resolve, reject) => {
    const server = createServer();
    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const address = server.address();
      server.close(() => resolve(address.port));
    });
  });
}

function snapshotTree(root) {
  const result = [];
  if (!statSafe(root)) return result;
  const walk = (directory) => {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
      } else {
        const stat = statSync(fullPath);
        result.push([path.relative(root, fullPath), stat.size, stat.mtimeMs]);
      }
    }
  };
  walk(root);
  return result.sort((left, right) => left[0].localeCompare(right[0]));
}

function statSafe(target) {
  try {
    return statSync(target);
  } catch {
    return null;
  }
}

function runPlaywright(args, env, output) {
  const cli = path.join(frontendRoot, 'node_modules', '@playwright', 'test', 'cli.js');
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [cli, 'test', ...args], {
      cwd: frontendRoot,
      env,
      stdio: ['inherit', 'pipe', 'pipe'],
    });
    const tee = (stream, destination) => stream.on('data', (chunk) => {
      destination.write(chunk);
      output.write(chunk);
    });
    tee(child.stdout, process.stdout);
    tee(child.stderr, process.stderr);
    child.on('error', reject);
    child.on('exit', (code) => resolve(code ?? 1));
    for (const signal of ['SIGINT', 'SIGTERM']) {
      process.once(signal, () => child.kill(signal));
    }
  });
}

const cliArgs = process.argv.slice(2);
const liveIndex = cliArgs.indexOf('--live');
const includeLive = liveIndex >= 0;
if (includeLive) cliArgs.splice(liveIndex, 1);

rmSync(artifactsDir, { recursive: true, force: true });
mkdirSync(logDir, { recursive: true });
const runtimeDir = await mkdtemp(path.join(os.tmpdir(), 'zhanfa-e2e-'));
let exitCode = 1;
let playwrightLog;
try {
  const reuseServers = !process.env.CI && process.env.E2E_REUSE_SERVERS === 'true';
  const backendPort = process.env.E2E_BACKEND_PORT ?? String(reuseServers ? 8000 : await freePort());
  const frontendPort = process.env.E2E_FRONTEND_PORT ?? String(reuseServers ? 5173 : await freePort());
  const dataDir = path.join(runtimeDir, 'data');
  const databasePath = path.join(runtimeDir, 'zhanfa-e2e.db').replaceAll('\\', '/');
  const workspaceData = path.join(repoRoot, 'data');
  const beforeData = snapshotTree(workspaceData);
  const runtimeLog = path.join(logDir, 'runtime.json');
  const env = {
    ...process.env,
    ZHANFA_E2E: '1',
    E2E_RUNTIME_DIR: runtimeDir,
    E2E_LOG_DIR: logDir,
    E2E_BACKEND_HOST: '127.0.0.1',
    E2E_BACKEND_PORT: backendPort,
    E2E_FRONTEND_PORT: frontendPort,
    E2E_INCLUDE_LIVE: includeLive ? 'true' : 'false',
    DATA_DIR: dataDir,
    DATABASE_URL: `sqlite:///${databasePath}`,
    CORS_ORIGINS: `http://127.0.0.1:${frontendPort}`,
    VITE_API_PROXY_TARGET: `http://127.0.0.1:${backendPort}`,
    VITE_ENABLE_MOCK: 'false',
    ZHANFA_DAILY_PROVIDER: includeLive
      ? (process.env.ZHANFA_LIVE_DAILY_PROVIDER ?? 'tencent')
      : 'fixture',
    ZHANFA_DAILY_FALLBACK_ENABLED: includeLive
      ? (process.env.ZHANFA_DAILY_FALLBACK_ENABLED ?? 'false')
      : 'false',
  };
  writeFileSync(
    runtimeLog,
    `${JSON.stringify({ runtimeDir, dataDir, databasePath, backendPort, frontendPort, reuseServers }, null, 2)}\n`,
    'utf8',
  );
  playwrightLog = createWriteStream(path.join(logDir, 'playwright.log'));
  exitCode = await runPlaywright(cliArgs, env, playwrightLog);
  const afterData = snapshotTree(workspaceData);
  if (JSON.stringify(beforeData) !== JSON.stringify(afterData)) {
    process.stderr.write('E2E isolation failure: workspace data/ changed during the run.\n');
    exitCode = 1;
  }
} finally {
  playwrightLog?.end();
  await rm(runtimeDir, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 });
  if (statSafe(runtimeDir)) {
    process.stderr.write(`E2E cleanup failure: ${runtimeDir}\n`);
    exitCode = 1;
  }
}

process.exitCode = exitCode;
