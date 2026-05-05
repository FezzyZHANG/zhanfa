declare module 'virtual:docs' {
  export interface DocEntry {
    path: string // e.g. 'docs/index.md'
    name: string // filename without .md
    title: string // first # heading text
    category: 'docs' | 'developer'
    content: string // raw markdown
  }

  const docs: DocEntry[]
  export default docs
}
