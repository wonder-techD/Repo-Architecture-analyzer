import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'

function slugify(text) {
  return text
    .trim()
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
}

export function extractHeadings(markdown) {
  if (!markdown) return []
  const lines = markdown.split('\n')
  const headings = []
  for (const line of lines) {
    const match = line.match(/^(#{1,3})\s+(.+)$/)
    if (match) {
      const level = match[1].length
      const text = match[2].trim()
      headings.push({ level, text, id: slugify(text) })
    }
  }
  return headings
}

export default function TOCSidebar({ headings, className = '' }) {
  const [activeId, setActiveId] = useState('')
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActiveId(entry.target.id)
            break
          }
        }
      },
      { rootMargin: '-80px 0% -70% 0%', threshold: 0 }
    )
    headings.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [headings])

  if (!headings.length) return null

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="lg:hidden w-full flex items-center justify-between px-4 py-3 rounded-xl border border-white/10 bg-codeRepo-surface text-sm text-slate-300 mb-4"
      >
        <span>On this page</span>
        <svg className={`w-4 h-4 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      <aside
        className={`${className} ${open ? 'block' : 'hidden'} lg:block lg:sticky lg:top-24 shrink-0 w-full lg:w-56`}
      >
        <nav className="space-y-1">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Contents</p>
          {headings.map(({ level, text, id }) => (
            <a
              key={id}
              href={`#${id}`}
              onClick={() => setOpen(false)}
              className={`block py-1.5 text-sm transition rounded-lg px-2 -mx-2 ${
                level === 2 ? 'pl-0 font-bold' : 'pl-4 font-normal'
              } ${
                activeId === id
                  ? 'text-indigo-300 bg-indigo-500/20'
                  : level === 2
                    ? 'text-white hover:text-indigo-300 hover:bg-white/5'
                    : 'text-slate-300 hover:text-indigo-200 hover:bg-white/5'
              }`}
              style={{ marginLeft: level === 3 ? '0.5rem' : 0 }}
            >
              {text}
            </a>
          ))}
        </nav>
      </aside>
    </>
  )
}
