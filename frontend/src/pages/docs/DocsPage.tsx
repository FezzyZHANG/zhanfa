import { useMemo, type ComponentPropsWithoutRef } from 'react'
import { useSearch, useNavigate, Link } from '@tanstack/react-router'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@/lib/utils'
import { getAllDocs, getDocByPath, getDocCategories } from '@/lib/docs'
import type { DocEntry } from '@/lib/docs'
import { Card, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'

function DocSidebar({
  docs,
  selectedPath,
  onSelect,
}: {
  docs: DocEntry[]
  selectedPath: string | null
  onSelect: (path: string) => void
}) {
  const categories = getDocCategories()

  return (
    <aside className="w-64 shrink-0 border-r border-border overflow-y-auto">
      <div className="pr-4 h-full">
        {categories.map((cat) => {
          const catDocs = docs.filter((d) => d.category === cat.key)
          if (catDocs.length === 0) return null

          const tickets = catDocs.filter((d) => d.path.startsWith('developer/tickets/'))
          const regular = catDocs.filter((d) => !d.path.startsWith('developer/tickets/'))

          return (
            <div key={cat.key} className="mb-6">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
                {cat.label}
              </h3>
              <ul className="space-y-0.5">
                {regular.map((doc) => (
                  <li key={doc.path}>
                    <button
                      onClick={() => onSelect(doc.path)}
                      className={cn(
                        'w-full text-left text-sm px-2 py-1.5 rounded-md transition-colors',
                        'hover:bg-accent hover:text-accent-foreground',
                        selectedPath === doc.path
                          ? 'bg-accent text-accent-foreground font-medium'
                          : 'text-muted-foreground',
                      )}
                    >
                      {doc.title}
                    </button>
                  </li>
                ))}
                {tickets.length > 0 && (
                  <>
                    <li>
                      <p className="text-xs text-muted-foreground px-2 pt-3 pb-1 font-medium">工单</p>
                    </li>
                    {tickets.map((doc) => (
                      <li key={doc.path}>
                        <button
                          onClick={() => onSelect(doc.path)}
                          className={cn(
                            'w-full text-left text-sm px-2 py-1.5 rounded-md transition-colors',
                            'hover:bg-accent hover:text-accent-foreground',
                            selectedPath === doc.path
                              ? 'bg-accent text-accent-foreground font-medium'
                              : 'text-muted-foreground',
                          )}
                        >
                          <span className="text-xs font-mono text-muted-foreground">
                            {doc.name.replace('TICKET-', '#')}
                          </span>
                          <span className="ml-1.5">{doc.title}</span>
                        </button>
                      </li>
                    ))}
                  </>
                )}
              </ul>
            </div>
          )
        })}
      </div>
    </aside>
  )
}

function DocBreadcrumb({ doc }: { doc: DocEntry }) {
  return (
    <div className="mb-6 flex items-center gap-2 text-sm text-muted-foreground">
      <Link to="/docs" search={{}} className="hover:text-foreground transition-colors">
        文档
      </Link>
      <span>/</span>
      <span>{doc.category === 'docs' ? '使用文档' : '开发者文档'}</span>
      <span>/</span>
      <span className="text-foreground">{doc.title}</span>
    </div>
  )
}

const markdownComponents = {
  pre: ({ children }: ComponentPropsWithoutRef<'pre'>) => <>{children}</>,
  code: ({ className, children, ...props }: ComponentPropsWithoutRef<'code'>) => {
    const match = /language-(\w+)/.exec(className || '')
    const isInline = !match && !className
    if (isInline) {
      return (
        <code className="markdown-inline-code" {...props}>
          {children}
        </code>
      )
    }
    return (
      <div className="markdown-code-block">
        {match && <div className="markdown-code-lang">{match[1]}</div>}
        <code className={cn(className, 'markdown-code')} {...props}>
          {children}
        </code>
      </div>
    )
  },
  table: ({ children }: ComponentPropsWithoutRef<'table'>) => (
    <div className="markdown-table-wrapper">
      <table className="markdown-table">{children}</table>
    </div>
  ),
  blockquote: ({ children }: ComponentPropsWithoutRef<'blockquote'>) => (
    <blockquote className="markdown-blockquote">{children}</blockquote>
  ),
  a: ({ children, href, ...props }: ComponentPropsWithoutRef<'a'>) => (
    <a href={href} className="markdown-link" target="_blank" rel="noopener noreferrer" {...props}>
      {children}
    </a>
  ),
  h1: ({ children }: ComponentPropsWithoutRef<'h1'>) => (
    <h1 className="markdown-h1">{children}</h1>
  ),
  h2: ({ children }: ComponentPropsWithoutRef<'h2'>) => (
    <h2 className="markdown-h2">{children}</h2>
  ),
  hr: () => <hr className="markdown-hr" />,
  img: ({ src, alt }: ComponentPropsWithoutRef<'img'>) => (
    <img src={src} alt={alt} className="markdown-img" />
  ),
}

function DocContent({ doc }: { doc: DocEntry }) {
  return (
    <div>
      <DocBreadcrumb doc={doc} />
      <article className="markdown-body">
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
          {doc.content}
        </ReactMarkdown>
      </article>
    </div>
  )
}

function DocsIndex() {
  const categories = getDocCategories()
  const allDocs = getAllDocs()

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight mb-2">文档</h1>
      <p className="text-muted-foreground mb-8">
        Zhanfa (战法) 项目文档 —— 使用指南与开发者参考
      </p>

      {categories.map((cat) => {
        const catDocs = allDocs
          .filter((d) => d.category === cat.key && !d.path.includes('/tickets/'))
          .slice(0, 5)

        return (
          <div key={cat.key} className="mb-8">
            <h2 className="text-lg font-semibold mb-3">{cat.label}</h2>
            <p className="text-sm text-muted-foreground mb-4">{cat.description}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {catDocs.map((doc) => (
                <Link
                  key={doc.path}
                  to="/docs"
                  search={{ file: doc.path }}
                  className="block"
                >
                  <Card className="h-full hover:shadow-md transition-shadow cursor-pointer">
                    <CardHeader>
                      <CardTitle className="text-base">{doc.title}</CardTitle>
                      <CardDescription className="text-xs font-mono">
                        {doc.path}
                      </CardDescription>
                    </CardHeader>
                  </Card>
                </Link>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function DocsPage() {
  const allDocs = useMemo(() => getAllDocs(), [])
  const { file } = useSearch({ from: '/docs' })
  const navigate = useNavigate()
  const selectedDoc = file ? getDocByPath(file) : undefined

  const handleSelect = (path: string) => {
    navigate({ to: '/docs', search: { file: path } })
  }

  return (
    <div className="flex gap-8 h-[calc(100vh-3.5rem-3rem)]">
      <DocSidebar docs={allDocs} selectedPath={file ?? null} onSelect={handleSelect} />
      <main className="flex-1 min-w-0 pb-16 overflow-y-auto">
        {selectedDoc ? <DocContent doc={selectedDoc} /> : <DocsIndex />}
      </main>
    </div>
  )
}
