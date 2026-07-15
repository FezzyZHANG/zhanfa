import { createWriteStream, mkdirSync } from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import process from 'node:process';

const kind = process.argv[2];
if (!['backend', 'frontend'].includes(kind)) {
  throw new Error('Usage: start-server.mjs <backend|frontend>');
}

const repoRoot = path.resolve(import.meta.dirname, '../../..');
const logDir = process.env.E2E_LOG_DIR ?? path.join(repoRoot, 'frontend', 'e2e-artifacts', 'logs');
mkdirSync(logDir, { recursive: true });
const log = createWriteStream(path.join(logDir, `${kind}.log`), { flags: 'a' });

const command = kind === 'backend'
  ? 'uv'
  : process.execPath;
const args = kind === 'backend'
  ? ['run', 'python', 'scripts/run_e2e_backend.py']
  : [
      process.env.npm_execpath,
      'run',
      'dev',
      '--',
      '--host',
      '127.0.0.1',
      '--port',
      process.env.E2E_FRONTEND_PORT ?? '5173',
      '--strictPort',
    ];
const cwd = kind === 'backend' ? repoRoot : path.join(repoRoot, 'frontend');
const child = spawn(command, args, { cwd, env: process.env, stdio: ['ignore', 'pipe', 'pipe'] });

function tee(stream, destination) {
  stream.on('data', (chunk) => {
    destination.write(chunk);
    log.write(chunk);
  });
}

tee(child.stdout, process.stdout);
tee(child.stderr, process.stderr);
child.on('error', (error) => {
  const message = `${kind} spawn failed: ${error.stack ?? error.message}\n`;
  process.stderr.write(message);
  log.write(message);
});
child.on('exit', (code, signal) => {
  log.end(`${kind} exited code=${code ?? 'null'} signal=${signal ?? 'none'}\n`);
  process.exitCode = code ?? 1;
});

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}
