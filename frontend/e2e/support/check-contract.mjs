import { mkdtemp, readdir, readFile, rm } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import os from 'node:os';
import process from 'node:process';

const frontendRoot = path.resolve(import.meta.dirname, '../..');
const repoRoot = path.resolve(frontendRoot, '..');
const expectedDir = path.join(frontendRoot, 'src', 'api', 'generated');

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? frontendRoot,
    env: options.env ?? process.env,
    stdio: 'inherit',
  });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}

async function files(root, directory = root) {
  const output = [];
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) output.push(...await files(root, fullPath));
    else output.push(path.relative(root, fullPath));
  }
  return output.sort();
}

async function compareDirectories(expected, actual) {
  const expectedFiles = await files(expected);
  const actualFiles = await files(actual);
  if (JSON.stringify(expectedFiles) !== JSON.stringify(actualFiles)) {
    return `generated file list differs\nexpected: ${expectedFiles.join(', ')}\nactual: ${actualFiles.join(', ')}`;
  }
  for (const file of expectedFiles) {
    const [left, right] = await Promise.all([
      readFile(path.join(expected, file), 'utf8'),
      readFile(path.join(actual, file), 'utf8'),
    ]);
    if (left.replaceAll('\r\n', '\n') !== right.replaceAll('\r\n', '\n')) {
      return `generated contract differs: ${file}`;
    }
  }
  return null;
}

run('uv', ['run', 'python', 'scripts/export_openapi.py', '--check', 'contracts/openapi.json'], {
  cwd: repoRoot,
});

const temporaryOutput = await mkdtemp(path.join(os.tmpdir(), 'zhanfa-openapi-'));
try {
  const cli = path.join(frontendRoot, 'node_modules', '@hey-api', 'openapi-ts', 'bin', 'run.js');
  run(process.execPath, [cli], {
    env: { ...process.env, ZHANFA_OPENAPI_OUTPUT: temporaryOutput },
  });
  const difference = await compareDirectories(expectedDir, temporaryOutput);
  if (difference) {
    process.stderr.write(`${difference}\nRun \`npm run contract:generate\` after an intentional API change.\n`);
    process.exitCode = 1;
  } else {
    process.stdout.write('Generated TypeScript API types are up to date.\n');
  }
} finally {
  await rm(temporaryOutput, { recursive: true, force: true });
}
