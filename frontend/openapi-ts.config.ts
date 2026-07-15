import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: '../contracts/openapi.json',
  output: {
    path: process.env.ZHANFA_OPENAPI_OUTPUT ?? 'src/api/generated',
    clean: true,
  },
  plugins: ['@hey-api/typescript'],
});
