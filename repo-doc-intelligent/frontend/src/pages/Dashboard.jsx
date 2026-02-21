import { useEffect, useState, useRef } from 'react'
import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import axios from 'axios'
import mermaid from 'mermaid'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function Dashboard() {
  const { jobId } = useParams()
  const [content, setContent] = useState(null)
  const [error, setError] = useState('')
  const [isDark, setIsDark] = useState(true)
  const mermaidRef = useRef(null)

  useEffect(() => {
    if (!jobId) return
    let cancelled = false
    axios
      .get(`${API_BASE}/content/${jobId}`)
      .then(({ data }) => {
        if (!cancelled) setContent(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || err.message || 'Failed to load content')
      })
    return () => { cancelled = true }
  }, [jobId])

  useEffect(() => {
    if (!content?.mermaid || !mermaidRef.current) return
    mermaid.initialize({ startOnLoad: false, theme: 'dark' })
    const el = mermaidRef.current
    el.innerHTML = ''
    const id = `mermaid-${jobId}`
    const pre = document.createElement('pre')
    pre.className = 'mermaid'
    pre.id = id
    pre.textContent = content.mermaid
    el.appendChild(pre)
    mermaid.run({ nodes: [pre] }).catch(() => {
      pre.textContent = content.mermaid
    })
  }, [jobId, content?.mermaid])

  if (error) {
    return (
      <div className="min-h-screen bg-codeRepo-dark flex flex-col">
        <DashboardHeader isDark={isDark} setIsDark={setIsDark} />
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="rounded-xl bg-codeRepo-surface border border-slate-700 p-8 max-w-md text-center">
            <p className="text-red-400">{error}</p>
            <Link to="/" className="mt-4 inline-block text-codeRepo-accent hover:underline">← New analysis</Link>
          </div>
        </div>
      </div>
    )
  }

  if (!content) {
    return (
      <div className="min-h-screen bg-codeRepo-dark flex flex-col">
        <DashboardHeader isDark={isDark} setIsDark={setIsDark} />
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="rounded-xl bg-codeRepo-surface border border-slate-700 p-8">
            <p className="text-slate-400">Loading report…</p>
            <div className="mt-4 h-1 w-48 bg-slate-700 rounded overflow-hidden">
              <div className="h-full bg-codeRepo-accent animate-pulse" style={{ width: '40%' }} />
            </div>
          </div>
        </div>
      </div>
    )
  }

  const { markdown, mermaid: mermaidSrc, metadata } = content
  const downloadUrl = `${API_BASE}/download/${jobId}`

  return (
    <div className="min-h-screen bg-codeRepo-dark text-white flex flex-col">
      <DashboardHeader isDark={isDark} setIsDark={setIsDark} />
      <div className="flex-1 flex flex-col lg:flex-row">
        <aside className="lg:w-72 shrink-0 bg-codeRepo-bg/80 border-b lg:border-b-0 lg:border-r border-slate-800 p-6">
          <Link to="/" className="text-sm text-slate-400 hover:text-codeRepo-accent mb-4 inline-block transition">← New analysis</Link>
          <h2 className="font-semibold text-white mb-4">Overview</h2>
          <dl className="space-y-3 text-sm">
            <div>
              <dt className="text-slate-500">Files</dt>
              <dd className="font-medium text-slate-200">{metadata?.file_count ?? 0}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Languages</dt>
              <dd className="text-slate-200">
                {metadata?.languages && Object.keys(metadata.languages).length > 0
                  ? Object.entries(metadata.languages).map(([k, v]) => (
                      <span key={k} className="mr-2">{k}: {v}</span>
                    ))
                  : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Frameworks</dt>
              <dd className="text-slate-200">
                {metadata?.frameworks?.length ? metadata.frameworks.join(', ') : '—'}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Entry points</dt>
              <dd className="text-slate-300 text-xs break-all">
                {metadata?.entry_points?.length
                  ? metadata.entry_points.slice(0, 5).map((ep) => <div key={ep}>{ep}</div>)
                  : '—'}
                {metadata?.entry_points?.length > 5 && (
                  <div>+{metadata.entry_points.length - 5} more</div>
                )}
              </dd>
            </div>
          </dl>
          <a
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-6 inline-block w-full rounded-xl bg-codeRepo-accent hover:bg-codeRepo-accent-hover text-white py-2.5 text-center font-medium transition"
          >
            Download PDF
          </a>
        </aside>
        <main className="flex-1 overflow-auto p-6 lg:p-8 bg-codeRepo-dark">
          <div className="max-w-3xl mx-auto space-y-8">
            <article className="prose prose-invert prose-slate max-w-none rounded-xl bg-codeRepo-surface border border-slate-700 p-6 lg:p-8 [&_pre]:bg-slate-900/80 [&_pre]:border-slate-700 [&_code]:bg-slate-800/60 [&_code]:text-slate-200 [&_pre_code]:bg-transparent [&_pre_code]:text-inherit [&_:not(pre)>code]:px-1 [&_:not(pre)>code]:rounded">
              <ReactMarkdown>{markdown || ''}</ReactMarkdown>
            </article>
            {mermaidSrc && (
              <section className="rounded-xl bg-codeRepo-surface border border-slate-700 p-6 overflow-x-auto">
                <h3 className="text-lg font-semibold text-white mb-4">Architecture diagram</h3>
                <div ref={mermaidRef} className="mermaid-container min-h-[200px]" />
              </section>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

function DashboardHeader({ isDark, setIsDark }) {
  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-codeRepo-bg/95 backdrop-blur-sm">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold text-white">
          Code-Repo
        </Link>
        <button
          type="button"
          onClick={() => setIsDark((d) => !d)}
          className="p-2 rounded-lg hover:bg-slate-800 text-slate-300 transition"
          aria-label="Toggle theme"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="5" />
            <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
          </svg>
        </button>
      </div>
    </header>
  )
}
