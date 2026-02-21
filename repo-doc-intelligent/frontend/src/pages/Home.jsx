import { useState, useEffect, useRef } from 'react'
import { flushSync } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_URL || ''

const ANALYSIS_STEPS = [
  'Cloning repository',
  'Scanning files and detecting languages',
  'Building symbol index and dependency graph',
  'Building call graph and resolving symbols',
  'Detecting entry points and architecture layers',
  'Computing metrics and responsibility classification',
  'Generating layer and module diagrams',
  'Generating Code Wiki documentation with AI',
  'Building RAG vectors for Q&A',
  'Finalizing report',
]

const NAV_LINKS = [
  'Application',
  'Core Capabilities',
  'Pricing',
  'How it works',
  'About us',
]

const CORE_CAPABILITIES = [
  {
    title: 'GitHub Content Hub',
    description: 'Unified AI assistant that aggregates and contextualizes data from your GitHub repository. Single point of reference. Fast content retrieval',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
        <path d="M12 8v8" />
        <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
      </svg>
    ),
  },
  {
    title: 'Customized PDF Layouts',
    description: 'Generate professional PDF documents with customizable layouts and formatting.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
        <line x1="12" y1="20" x2="12" y2="10" />
        <line x1="18" y1="20" x2="18" y2="4" />
        <line x1="6" y1="20" x2="6" y2="16" />
      </svg>
    ),
    badgeColors: ['#4285f4', '#0f9d58', '#db4437', '#f4b400'],
  },
  {
    title: 'Agentic Workflow',
    description: 'Automates the entire GitHub to PDF conversion process, from fetching content to formatting. Automated content fetching. Structured PDF generation. Version control integration (optional)',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
        <circle cx="12" cy="12" r="10" />
        <circle cx="12" cy="12" r="6" />
        <circle cx="12" cy="12" r="2" />
      </svg>
    ),
  },
  {
    title: 'Content Structuring',
    description: 'AI-powered structuring and organization of repository content for clear, logical PDF output.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
        <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.64 5.64l1.42 1.42M16.94 16.94l1.42 1.42M5.64 18.36l1.42-1.42M16.94 7.06l1.42-1.42" />
        <rect x="8" y="8" width="8" height="10" rx="1" />
      </svg>
    ),
  },
  {
    title: 'Continuous Learning',
    description: 'Improves output quality over time by learning from your preferences and document patterns.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
        <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v3a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" />
        <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v3a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
        <path d="M12 12v4" />
        <path d="M9 22h6" />
      </svg>
    ),
  },
  {
    title: 'Real-time Progress & Alerts',
    description: 'Track conversion status and get notified when your PDF is ready or if attention is needed.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
  },
]

export default function Home() {
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [completedSteps, setCompletedSteps] = useState(0)
  const [todosExpanded, setTodosExpanded] = useState(true)
  const [error, setError] = useState('')
  const [isDark, setIsDark] = useState(true)
  const navigate = useNavigate()
  const loadingBlockRef = useRef(null)

  useEffect(() => {
    if (!loading) {
      setCompletedSteps(0)
      return
    }
    setCompletedSteps(0)
    const interval = setInterval(() => {
      setCompletedSteps((n) => Math.min(n + 1, ANALYSIS_STEPS.length))
    }, 2200)
    return () => clearInterval(interval)
  }, [loading])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const url = (repoUrl || '').trim()
    if (!url) {
      setError('Enter a GitHub repository URL.')
      return
    }
    // Force React to commit loading state and paint the to-do list before the request blocks the thread
    flushSync(() => {
      setLoading(true)
      setCompletedSteps(0)
      setTodosExpanded(true)
    })
    // Defer scroll so the loading block ref is attached after the conditional render
    requestAnimationFrame(() => {
      loadingBlockRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    })
    try {
      const { data } = await axios.post(`${API_BASE}/analyze`, { repo_url: url })
      setCompletedSteps(ANALYSIS_STEPS.length)
      setTimeout(() => navigate(`/dashboard/${data.job_id}`), 400)
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Analysis failed.'
      setError(Array.isArray(msg) ? msg.join(' ') : msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className={`min-h-screen transition-colors ${
        isDark ? 'bg-codeRepo-dark text-white' : 'bg-slate-50 text-slate-900'
      }`}
    >
      {/* Header */}
      <header
        className={`sticky top-0 z-50 border-b ${
          isDark ? 'bg-codeRepo-bg/95 border-slate-800' : 'bg-white/95 border-slate-200'
        } backdrop-blur-sm`}
      >
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <a href="/" className="text-xl font-semibold">
            Code-Repo
          </a>
          <nav className="flex items-center gap-4 md:gap-8">
            {NAV_LINKS.map((label) => (
              <a
                key={label}
                href="#"
                className={`hidden lg:inline text-sm font-bold text-white hover:text-codeRepo-accent transition ${
                  isDark ? 'text-white hover:text-codeRepo-accent' : 'text-white hover:text-codeRepo-accent'
                }`}
              >
                {label}
              </a>
            ))}
            <a
              href="#"
              className={`hidden sm:inline text-sm font-medium hover:text-codeRepo-accent transition ${
                isDark ? 'text-slate-300' : 'text-slate-600'
              }`}
            >
              Sign In
            </a>
            <button
              type="button"
              onClick={() => setIsDark(!isDark)}
              className={`p-2 rounded-lg transition ${
                isDark ? 'hover:bg-slate-800 text-slate-300' : 'hover:bg-slate-200 text-slate-600'
              }`}
              aria-label="Toggle theme"
            >
              {isDark ? (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="max-w-4xl mx-auto px-6 pt-20 pb-32">
        <h1 className="text-4xl md:text-5xl font-bold text-center tracking-tight leading-tight mb-6">
          Convert GitHub Repositories to PDF{' '}
          <span className="text-codeRepo-accent">Instantly</span>
        </h1>
        <p
          className={`text-center text-lg max-w-2xl mx-auto mb-12 ${
            isDark ? 'text-slate-400' : 'text-slate-600'
          }`}
        >
          Transform your codebase, documentation, or project files from GitHub into
          professional PDF documents with AI, no code required.
        </p>

        {/* Input */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div
            className={`flex rounded-xl border overflow-hidden ${
              isDark ? 'bg-codeRepo-surface border-slate-700' : 'bg-white border-slate-200 shadow-sm'
            }`}
          >
            <input
              type="url"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="Enter GitHub repo URL or ask about converting code to PDF..."
              className={`flex-1 px-5 py-4 bg-transparent text-base placeholder-slate-500 focus:outline-none ${
                isDark ? 'text-white' : 'text-slate-900'
              }`}
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 bg-codeRepo-accent hover:bg-codeRepo-accent-hover text-white font-medium disabled:opacity-60 disabled:cursor-not-allowed transition shrink-0"
            >
              Send
            </button>
          </div>
          {error && (
            <p className="text-sm text-red-400 text-center" role="alert">
              {error}
            </p>
          )}
          {loading && (
            <div
              ref={loadingBlockRef}
              className="rounded-xl border bg-codeRepo-surface/80 border-slate-700 overflow-hidden"
              role="status"
              aria-live="polite"
              aria-label="Analysis in progress"
            >
              <button
                type="button"
                onClick={() => setTodosExpanded(!todosExpanded)}
                className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-slate-800/50 transition"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className={`transition-transform ${todosExpanded ? 'rotate-180' : ''}`}
                >
                  <path d="M6 9l6 6 6-6" />
                </svg>
                <span className="text-slate-300">Analysis in progress</span>
                <span className="text-slate-500 ml-1">{completedSteps}/{ANALYSIS_STEPS.length}</span>
              </button>
              {todosExpanded && (
                <ul className="border-t border-slate-700 px-4 py-3 space-y-2">
                  {ANALYSIS_STEPS.map((step, i) => (
                    <li
                      key={step}
                      className={`flex items-center gap-3 text-sm ${
                        i < completedSteps
                          ? 'text-slate-400 line-through'
                          : i === completedSteps
                            ? 'text-codeRepo-accent'
                            : 'text-slate-500'
                      }`}
                    >
                      <span className="shrink-0 w-5 h-5 rounded-full border flex items-center justify-center">
                        {i < completedSteps ? (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M20 6L9 17l-5-5" />
                          </svg>
                        ) : i === completedSteps ? (
                          <span className="w-2 h-2 rounded-full bg-codeRepo-accent animate-pulse" />
                        ) : null}
                      </span>
                      {step}{i === completedSteps ? '…' : ''}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {!loading && (
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              type="button"
              onClick={() => {
                setRepoUrl('https://github.com/ss94866/nilaapps-task')
                document.querySelector('input[type="url"]')?.focus()
              }}
              className="w-full sm:w-auto px-8 py-3 rounded-xl border-2 border-codeRepo-accent text-codeRepo-accent font-medium hover:bg-codeRepo-accent/10 transition"
            >
              See Demo
            </button>
            <button
              type="button"
              onClick={() => document.querySelector('input[type="url"]')?.focus()}
              className="w-full sm:w-auto px-8 py-3 rounded-xl bg-codeRepo-accent hover:bg-codeRepo-accent-hover text-white font-medium transition"
            >
              Get Started
            </button>
          </div>
          )}
        </form>
      </main>

      {/* Core Capabilities */}
      <section
        id="core-capabilities"
        className={`py-20 md:py-28 ${
          isDark ? 'bg-codeRepo-bg' : 'bg-slate-100'
        }`}
      >
        <div className="max-w-6xl mx-auto px-6">
          <h2
            className={`text-3xl md:text-4xl font-bold text-center tracking-tight mb-4 ${
              isDark ? 'text-white' : 'text-slate-900'
            }`}
          >
            Core Capabilities for GitHub to PDF Conversion
          </h2>
          <p
            className={`text-center text-lg max-w-2xl mx-auto mb-14 ${
              isDark ? 'text-slate-400' : 'text-slate-600'
            }`}
          >
            Leverage comprehensive AI solutions to seamlessly transform your GitHub content into structured PDFs.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {CORE_CAPABILITIES.map((cap) => (
              <div
                key={cap.title}
                className={`rounded-2xl border p-6 flex flex-col ${
                  isDark
                    ? 'bg-codeRepo-surface/80 border-slate-700/80 text-white'
                    : 'bg-white border-slate-200 shadow-sm text-slate-900'
                }`}
              >
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 mb-4 ${
                    isDark ? 'bg-codeRepo-accent/20 text-codeRepo-accent' : 'bg-indigo-100 text-codeRepo-accent'
                  }`}
                >
                  {cap.icon}
                </div>
                <h3 className="text-lg font-semibold mb-2">{cap.title}</h3>
                <p
                  className={`text-sm flex-1 ${
                    isDark ? 'text-slate-400' : 'text-slate-600'
                  }`}
                >
                  {cap.description}
                </p>
                {cap.badgeColors && (
                  <div className="flex gap-2 mt-4">
                    {cap.badgeColors.map((color, i) => (
                      <span
                        key={i}
                        className="w-8 h-8 rounded-lg shrink-0"
                        style={{ backgroundColor: color }}
                        aria-hidden
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}
