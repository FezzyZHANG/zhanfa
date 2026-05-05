import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { resolve, relative, extname, join } from 'node:path'

function walkDir(dir: string): string[] {
  const files: string[] = []
  if (!existsSync(dir)) return files
  for (const entry of readdirSync(dir)) {
    const fullPath = join(dir, entry)
    if (statSync(fullPath).isDirectory()) {
      files.push(...walkDir(fullPath))
    } else if (extname(entry) === '.md') {
      files.push(fullPath)
    }
  }
  return files
}

function docsPlugin() {
  const virtualModuleId = 'virtual:docs'
  const resolvedVirtualModuleId = '\0' + virtualModuleId

  return {
    name: 'docs-plugin',
    resolveId(id: string) {
      if (id === virtualModuleId) return resolvedVirtualModuleId
    },
    load(id: string) {
      if (id === resolvedVirtualModuleId) {
        const root = resolve(__dirname, '..')
        const docsDir = join(root, 'docs')
        const devDir = join(root, 'developer')

        const allFiles = [
          ...walkDir(docsDir).map((f) => ({ path: `docs/${relative(docsDir, f).replace(/\\/g, '/')}`, category: 'docs' as const })),
          ...walkDir(devDir).map((f) => ({ path: `developer/${relative(devDir, f).replace(/\\/g, '/')}`, category: 'developer' as const })),
        ]

        const entries = allFiles.map(({ path: relPath, category }) => {
          const fullPath = category === 'docs' ? join(docsDir, relPath.replace('docs/', '')) : join(devDir, relPath.replace('developer/', ''))
          const content = readFileSync(fullPath, 'utf-8')
          const name = relPath.split('/').pop()!.replace(/\.md$/, '')
          const title = content.match(/^#\s+(.+)/m)?.[1] ?? name
          return { path: relPath, name, title, category, content }
        })

        return `export default ${JSON.stringify(entries)}`
      }
    },
  }
}

export default defineConfig({
  plugins: [docsPlugin(), react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    fs: {
      allow: ['..'],
    },
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
