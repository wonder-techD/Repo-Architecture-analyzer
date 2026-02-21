import { useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import mermaid from 'mermaid'

function slugify(text) {
  return String(text)
    .trim()
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

function Heading({ level, children, ...props }) {
  const Tag = `h${level}`
  const text = typeof children === 'string' ? children : (Array.isArray(children) ? children.filter(c => typeof c === 'string').join('') : '')
  const id = slugify(text) || `heading-${level}-${Math.random().toString(36).slice(2)}`
  return <Tag id={id} className="scroll-mt-24" {...props}>{children}</Tag>
}

function MermaidBlock({ content }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current || !content) return
    mermaid.initialize({ startOnLoad: false, theme: 'dark' })
    const id = `mermaid-${Math.random().toString(36).slice(2)}`
    ref.current.innerHTML = ''
    const pre = document.createElement('pre')
    pre.className = 'mermaid'
    pre.id = id
    pre.textContent = content
    ref.current.appendChild(pre)
    mermaid.run({ nodes: [pre] }).catch(() => {
      pre.textContent = content
    })
  }, [content])
  return (
    <div className="my-6 rounded-xl border border-white/10 bg-codeRepo-bg/50 p-4 overflow-x-auto" ref={ref} />
  )
}

function Code({ node, className, children, ...props }) {
  const match = /language-(\w+)/.exec(className || '')
  const isMermaid = match?.[1] === 'mermaid'
  if (isMermaid) {
    return <MermaidBlock content={String(children).replace(/\n$/, '')} />
  }
  return (
    <code className={className} {...props}>
      {children}
    </code>
  )
}

export default function MarkdownContent({ markdown }) {
  if (!markdown) return null
  return (
    <article className="prose prose-invert prose-slate max-w-none prose-headings:scroll-mt-24 prose-h1:text-2xl prose-h2:text-xl prose-h2:mt-8 prose-h2:mb-4 prose-h2:pb-2 prose-h2:border-b prose-h2:border-white/10 prose-h3:text-lg prose-h3:mt-6 prose-p:text-slate-300 prose-p:leading-relaxed prose-a:text-indigo-400 prose-a:no-underline hover:prose-a:underline prose-strong:text-white prose-code:text-slate-200 prose-code:bg-white/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-pre:bg-codeRepo-bg prose-pre:border prose-pre:border-white/10">
      <ReactMarkdown
        components={{
          h1: (p) => <Heading level={1} {...p} />,
          h2: (p) => <Heading level={2} {...p} />,
          h3: (p) => <Heading level={3} {...p} />,
          code: Code,
        }}
      >
        {markdown}
      </ReactMarkdown>
    </article>
  )
}
