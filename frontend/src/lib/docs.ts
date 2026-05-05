import allDocs from 'virtual:docs'

export interface DocEntry {
  path: string
  name: string
  title: string
  category: 'docs' | 'developer'
  content: string
}

const docs = allDocs as DocEntry[]

export function getAllDocs(): DocEntry[] {
  return docs
}

export function getDocsByCategory(category: 'docs' | 'developer'): DocEntry[] {
  return docs.filter((d) => d.category === category)
}

export function getDocByPath(path: string): DocEntry | undefined {
  return docs.find((d) => d.path === path)
}

export function getDocCategories() {
  return [
    { key: 'docs' as const, label: '使用文档', description: '用户使用指南' },
    { key: 'developer' as const, label: '开发者文档', description: '开发者指南与工单跟踪' },
  ]
}
