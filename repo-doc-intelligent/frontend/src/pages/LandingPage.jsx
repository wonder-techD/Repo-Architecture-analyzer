import { useState, useRef, useEffect } from 'react'
import { flushSync } from 'react-dom'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Send, Sparkles, PanelLeftClose, Star, Clock, FileText, ClipboardList, Puzzle, MessageCircle, Copy, Download, Share2, Globe, User, Sun, Moon, Circle, Zap, Layers, Crown, Check, GitBranch } from 'lucide-react'
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

function getStoredTheme() {
  try {
    return localStorage.getItem('theme') !== 'light'
  } catch {
    return true
  }
}

export default function LandingPage() {
  const [repoUrl, setRepoUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [completedSteps, setCompletedSteps] = useState(0)
  const [todosExpanded, setTodosExpanded] = useState(true)
  const [error, setError] = useState('')
  const [isDark, setIsDark] = useState(getStoredTheme)
  const [billing, setBilling] = useState('monthly')
  const navigate = useNavigate()
  const location = useLocation()
  const loadingBlockRef = useRef(null)

  useEffect(() => {
    const hash = location.hash.slice(1)
    if (hash) {
      const el = document.getElementById(hash)
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }
    }
  }, [location.pathname, location.hash])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
    try {
      localStorage.setItem('theme', isDark ? 'dark' : 'light')
    } catch {}
  }, [isDark])

  // Advance completed steps on an interval while loading (so UI shows progress)
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
      setCompletedSteps(0) // Start with no steps completed - show as in progress
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
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-codeRepo-dark text-white">
      <div className="absolute inset-0 bg-gradient-glow pointer-events-none" />
      <header className="sticky top-0 z-50 border-b border-white/5 bg-codeRepo-bg/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <a href="/" className="text-2xl font-bold tracking-tight flex items-baseline gap-0.5">
            <span className="text-white font-bold">Code</span>
            <span className="text-slate-400 font-normal">-</span>
            <span className="bg-gradient-accent bg-clip-text text-transparent font-bold">Repo</span>
          </a>
          <nav className="hidden md:flex items-center gap-8">
            {NAV_LINKS.map((label) => {
              const hash = {
                'Application': 'application',
                'Core Capabilities': 'core-capabilities',
                'Pricing': 'pricing',
                'How it works': 'how-it-works',
                'About us': 'about-us',
              }[label] || label.toLowerCase().replace(/\s+/g, '-')
              return (
                <a
                  key={label}
                  href={`#${hash}`}
                  className="text-sm font-bold text-white hover:text-white/90 transition"
                >
                  {label}
                </a>
              )
            })}
            <button
              type="button"
              onClick={() => setIsDark((d) => !d)}
              className="p-2 rounded-lg text-white hover:bg-white/10 transition focus:outline-none focus:ring-2 focus:ring-indigo-500"
              aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
          </nav>
        </div>
      </header>

      <main id="application" className="relative min-h-[calc(100vh-4rem)] max-w-4xl mx-auto px-6 pt-24 pb-32 flex flex-col">
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-4xl md:text-6xl font-bold text-center tracking-tight leading-tight mb-6"
        >
          Convert GitHub Repositories to PDF{' '}
          <span className="bg-gradient-accent bg-clip-text text-transparent">Instantly</span>
        </motion.h1>
        <motion.p
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-center text-lg text-slate-400 max-w-2xl mx-auto mb-12"
        >
          Transform your codebase into professional documentation and PDF reports with AI—no code required.
        </motion.p>

        <motion.form
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          onSubmit={handleSubmit}
          className="space-y-6"
        >
          <div className="repo-url-search-box flex rounded-xl border border-white/10 bg-codeRepo-surface/80 overflow-hidden shadow-xl shadow-indigo-500/5 hover:border-white/15 transition">
            <input
              type="url"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="flex-1 px-5 py-4 bg-transparent text-white placeholder-slate-500 focus:outline-none text-base"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-4 bg-gradient-accent hover:opacity-95 text-white font-medium disabled:opacity-50 transition shrink-0 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
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
              className="rounded-xl border border-white/10 bg-codeRepo-surface/80 overflow-hidden"
              role="status"
              aria-live="polite"
              aria-label="Analysis in progress"
            >
              <button
                type="button"
                onClick={() => setTodosExpanded(!todosExpanded)}
                className="w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/5 transition"
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
                <ul className="border-t border-white/10 px-4 py-3 space-y-2">
                  {ANALYSIS_STEPS.map((step, i) => (
                    <li
                      key={step}
                      className={`flex items-center gap-3 text-sm ${
                        i < completedSteps
                          ? 'text-slate-400 line-through'
                          : i === completedSteps
                            ? 'text-indigo-400'
                            : 'text-slate-500'
                      }`}
                    >
                      <span className="shrink-0 w-5 h-5 rounded-full border flex items-center justify-center">
                        {i < completedSteps ? (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M20 6L9 17l-5-5" />
                          </svg>
                        ) : i === completedSteps ? (
                          <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                        ) : null}
                      </span>
                      {step}{i === completedSteps ? '…' : ''}
                    </li>
                  ))}
                </ul>
              )}
              <p className="border-t border-white/10 px-4 py-3 text-sm text-slate-400 text-center">
                Please wait…
              </p>
            </div>
          )}
          {!loading && (
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              type="button"
              onClick={() => setRepoUrl('https://github.com/ss94866/nilaapps-task')}
              className="w-full sm:w-auto px-8 py-3 rounded-xl border-2 border-slate-500 text-slate-300 font-medium hover:border-slate-400 hover:text-white transition"
            >
              See Demo
            </button>
            <button
              type="button"
              onClick={() => document.querySelector('input[type="url"]')?.focus()}
              className="w-full sm:w-auto px-8 py-3 rounded-xl bg-gradient-accent text-white font-medium hover:opacity-95 transition flex items-center justify-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              Get Started
            </button>
          </div>
          )}
        </motion.form>

        {/* Hero filler: short flow + scroll cue */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
          className="flex-1 flex flex-col justify-center pt-16 pb-8"
        >
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8 text-center">
            <div className="rounded-xl border border-white/10 bg-codeRepo-surface/40 px-6 py-5">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center mx-auto mb-3 text-indigo-400">
                <GitBranch className="w-5 h-5" />
              </div>
              <p className="text-white font-medium mb-1">Paste repo URL</p>
              <p className="text-slate-400 text-sm">Any public GitHub repository</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-codeRepo-surface/40 px-6 py-5">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center mx-auto mb-3 text-indigo-400">
                <Sparkles className="w-5 h-5" />
              </div>
              <p className="text-white font-medium mb-1">AI analyzes & documents</p>
              <p className="text-slate-400 text-sm">Structure, dependencies, architecture</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-codeRepo-surface/40 px-6 py-5">
              <div className="w-10 h-10 rounded-lg bg-indigo-500/20 flex items-center justify-center mx-auto mb-3 text-indigo-400">
                <FileText className="w-5 h-5" />
              </div>
              <p className="text-white font-medium mb-1">Get your PDF</p>
              <p className="text-slate-400 text-sm">Download or view in browser</p>
            </div>
          </div>
          <p className="text-slate-500 text-sm text-center mt-10">
            Scroll to explore capabilities
          </p>
        </motion.div>
      </main>

      {/* Core Capabilities */}
      <section id="core-capabilities" className="relative py-20 md:py-28 bg-codeRepo-bg">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center tracking-tight text-white mb-4">
            Core Capabilities for GitHub to PDF Conversion
          </h2>
          <p className="text-center text-lg text-slate-400 max-w-2xl mx-auto mb-14">
            Leverage comprehensive AI solutions to seamlessly transform your GitHub content into structured PDFs.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {CORE_CAPABILITIES.map((cap) => (
              <div
                key={cap.title}
                className="rounded-2xl border border-white/10 bg-codeRepo-surface/80 p-6 flex flex-col text-white"
              >
                <div className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0 mb-4 bg-indigo-500/20 text-indigo-400">
                  {cap.icon}
                </div>
                <h3 className="text-lg font-semibold mb-2">{cap.title}</h3>
                <p className="text-sm text-slate-400 flex-1">
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

      {/* How It Works - Interactive panel */}
      <section id="how-it-works" className="relative py-20 md:py-28 bg-codeRepo-dark">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center tracking-tight text-white mb-4">
            How It Works: GitHub to PDF Conversion
          </h2>
          <p className="text-center text-lg text-slate-400 max-w-2xl mx-auto mb-14">
            Input your GitHub repository URL, and our AI agent will process the content, structuring it into a transparent, high-quality PDF.
          </p>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="rounded-2xl border border-white/10 bg-codeRepo-bg overflow-hidden shadow-2xl"
          >
            {/* Panel top bar */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-codeRepo-surface/80">
              <div className="flex items-center gap-1">
                <span className="px-3 py-1.5 rounded-lg bg-indigo-500/20 text-indigo-300 text-sm font-medium">Code-Repo</span>
                <span className="px-3 py-1.5 rounded-lg text-slate-500 text-sm">Gallery</span>
              </div>
              <div className="flex items-center gap-3 flex-wrap justify-end">
                <span className="text-xs text-slate-500 font-mono max-w-[140px] truncate">https://app.coderepo.com/replay/3765d519…</span>
                <button type="button" className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/10 text-slate-400 hover:text-white text-xs">
                  <Copy className="w-3.5 h-3.5" /> Copy
                </button>
                <button type="button" className="px-2.5 py-1.5 rounded-lg bg-indigo-500/30 text-indigo-300 text-xs font-medium">Publish</button>
                <button type="button" className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-white/10 text-slate-400 hover:text-white text-xs">
                  <Download className="w-3.5 h-3.5" /> Download
                </button>
                <button type="button" className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white text-xs">
                  <Share2 className="w-3.5 h-3.5" /> Share
                </button>
                <button type="button" className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-slate-400 hover:text-white text-xs">
                  <Globe className="w-3.5 h-3.5" /> English
                </button>
                <span className="flex items-center gap-1.5 text-slate-400 text-xs">
                  <User className="w-3.5 h-3.5" /> Code-Repo - admin
                </span>
              </div>
            </div>

            <div className="flex flex-col lg:flex-row min-h-[420px]">
              {/* Left sidebar */}
              <nav className="lg:w-14 w-full shrink-0 flex flex-row lg:flex-col items-center justify-center lg:justify-start py-3 lg:py-4 gap-1 border-b lg:border-b-0 lg:border-r border-white/10 bg-codeRepo-surface/50">
                {[
                  { Icon: PanelLeftClose, label: 'Expand' },
                  { Icon: Star, label: 'New Task' },
                  { Icon: Clock, label: 'History' },
                  { Icon: FileText, label: 'Files' },
                  { Icon: ClipboardList, label: 'Plans' },
                  { Icon: Puzzle, label: 'Integrations' },
                  { Icon: MessageCircle, label: 'Prompt' },
                ].map(({ Icon, label }) => (
                  <button
                    key={label}
                    type="button"
                    className="flex flex-col items-center gap-1 p-2 rounded-lg text-slate-500 hover:text-indigo-400 hover:bg-white/5 transition"
                    title={label}
                  >
                    <Icon className="w-5 h-5" />
                    <span className="text-[10px]">{label}</span>
                  </button>
                ))}
              </nav>

              {/* Main content: Agent chat + Browser preview */}
              <div className="flex-1 flex flex-col lg:flex-row min-w-0">
                {/* Agent Configuration / chat */}
                <div className="flex-1 flex flex-col min-w-0 border-r border-white/10">
                  <div className="flex gap-1 px-4 py-2 border-b border-white/10">
                    <span className="px-3 py-1.5 rounded-t-lg bg-indigo-500/20 text-indigo-300 text-sm font-medium">Agent Configuration</span>
                    <span className="px-3 py-1.5 rounded-t-lg text-slate-500 text-sm">General Agent</span>
                  </div>
                  <div className="flex-1 overflow-auto p-4 text-sm text-slate-300 space-y-3">
                    <p className="font-medium text-slate-200">Computer Agent</p>
                    <div className="space-y-2 pl-2 border-l-2 border-indigo-500/50">
                      <p>Now for step 4, let me guide you through the interactive features of the charts:</p>
                      <p className="font-medium text-slate-200">1. Static PNG Chart Features</p>
                      <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                        <li>Clear visualization of browser market shares</li>
                        <li>Chrome dominates with 71.3% market share</li>
                        <li>Safari follows with 17.0%</li>
                        <li>Edge has 5.2%</li>
                        <li>Other browsers (Firefox, Samsung internet, Opera) have smaller shares</li>
                        <li>Color-coded legend for easy identification</li>
                      </ul>
                      <p className="font-medium text-slate-200 pt-1">2. Interactive HTML Chart Features (in the browser)</p>
                      <ul className="list-disc list-inside space-y-0.5 text-slate-400">
                        <li>Hover over segments to see exact percentages</li>
                        <li>Click legend items to hide/show specific browsers</li>
                        <li>Interactive tooltip with detailed information</li>
                        <li>Can be zoomed and panned if needed</li>
                      </ul>
                      <p className="pt-1">Let me update step 4 as completed.</p>
                      <p>Let me check the final plan status.</p>
                    </div>
                  </div>
                </div>

                {/* Right: Computer / Screenshot + embedded browser */}
                <div className="lg:w-[380px] w-full shrink-0 flex flex-col bg-codeRepo-surface/30 border-t lg:border-t-0 border-white/10">
                  <div className="flex gap-1 px-3 py-2 border-b border-white/10">
                    <span className="px-2 py-1 rounded-t text-indigo-300 text-xs font-medium">Computer</span>
                    <span className="px-2 py-1 rounded-t text-slate-500 text-xs">Screenshot</span>
                  </div>
                  <div className="flex-1 flex flex-col p-2 min-h-0">
                    <div className="rounded-lg border border-white/10 bg-slate-900/80 overflow-hidden flex-1 flex flex-col min-h-[280px]">
                      <div className="flex items-center gap-2 px-3 py-2 border-b border-white/10 bg-slate-800/80">
                        <span className="text-[10px] text-slate-500 font-mono truncate">file:///.../browser_share_static.png</span>
                      </div>
                      <div className="flex-1 flex items-center justify-center p-4">
                        {/* Pie chart - Browser Market Share */}
                        <div className="w-full max-w-[240px]">
                          <p className="text-center text-slate-200 font-semibold text-sm mb-3">Browser Market Share - June 2025</p>
                          <div
                            className="w-40 h-40 rounded-full mx-auto border-2 border-slate-700/50"
                            style={{
                              background: `conic-gradient(
                                #dc2626 0% 71.3%,
                                #0d9488 71.3% 88.3%,
                                #0284c7 88.3% 93.5%,
                                #a855f7 93.5% 96%,
                                #f59e0b 96% 98.1%,
                                #ec4899 98.1% 100%
                              )`,
                            }}
                          />
                          <div className="flex flex-wrap justify-center gap-x-3 gap-y-1 mt-3 text-[10px] text-slate-400">
                            <span><span className="inline-block w-2 h-2 rounded-full bg-red-600 mr-1" />Chrome 71.3%</span>
                            <span><span className="inline-block w-2 h-2 rounded-full bg-teal-600 mr-1" />Safari 17%</span>
                            <span><span className="inline-block w-2 h-2 rounded-full bg-sky-600 mr-1" />Edge 5.2%</span>
                            <span><span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1" />Others</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      <section id="pricing" className="relative py-20 md:py-28 bg-codeRepo-bg">
        <div className="max-w-6xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center tracking-tight text-white mb-4">Pricing</h2>
          <p className="text-center text-lg text-slate-400 max-w-2xl mx-auto mb-10">
            Four different subscriptions to match your companies' needs.
          </p>

          <div className="flex justify-center gap-2 mb-14">
            <button
              type="button"
              onClick={() => setBilling('monthly')}
              className={`px-6 py-2.5 rounded-lg text-sm font-medium transition ${billing === 'monthly' ? 'bg-indigo-600 text-white' : 'bg-white/10 text-slate-400 hover:text-white'}`}
            >
              Monthly
            </button>
            <button
              type="button"
              onClick={() => setBilling('annually')}
              className={`px-6 py-2.5 rounded-lg text-sm font-medium transition ${billing === 'annually' ? 'bg-indigo-600 text-white' : 'bg-white/10 text-slate-400 hover:text-white'}`}
            >
              Annually
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            {/* Free Tier */}
            <div className="rounded-2xl border border-white/10 bg-codeRepo-surface/80 p-6 flex flex-col">
              <div className="flex items-center gap-2 mb-2">
                <Circle className="w-5 h-5 text-slate-400" strokeWidth={1.5} />
                <h3 className="text-lg font-semibold text-white">Free Tier</h3>
              </div>
              <p className="text-sm text-slate-400 mb-4">Basic usage with monthly quota</p>
              <div className="mb-4">
                <span className="text-3xl font-bold text-white">$0</span>
                <span className="text-slate-400 ml-1">Forever free</span>
              </div>
              <ul className="space-y-3 flex-1 mb-6">
                {['200 credits per month', 'Approximately 1 task', 'Maximum 10 file exports', 'Limited uploads and file storage', '1 concurrent task'].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                    <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button type="button" className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition border border-indigo-500/50">
                Start free trial
              </button>
            </div>

            {/* Starter Tier */}
            <div className="rounded-2xl border border-white/10 bg-codeRepo-surface/80 p-6 flex flex-col relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 py-1.5 text-center text-xs font-medium bg-gradient-to-r from-pink-500/90 to-purple-500/90 text-white">
                Early Adopters Discount - 50% Off
              </div>
              <div className="pt-6 flex items-center gap-2 mb-2">
                <Zap className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-semibold text-white">Starter Tier</h3>
              </div>
              <p className="text-sm text-slate-400 mb-4">Starter plan with monthly quota</p>
              <div className="mb-2 flex items-baseline gap-2 flex-wrap">
                <span className="text-3xl font-bold text-white">$25</span>
                <span className="text-slate-400">/month</span>
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-pink-500/80 text-white">-50%</span>
              </div>
              <p className="text-xs text-slate-500 line-through mb-4">$49/month</p>
              <p className="text-xs text-slate-500 mb-4">Billed monthly - First month only</p>
              <ul className="space-y-3 flex-1 mb-6">
                {['8,000 credits per month', 'Approximately 15-40 tasks', 'Unlimited file exports', 'Unlimited uploads and file storage', '3 concurrent tasks'].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                    <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button type="button" className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition border border-indigo-500/50">
                Start free trial
              </button>
            </div>

            {/* ADVANCED */}
            <div className="rounded-2xl border border-white/10 bg-codeRepo-surface/80 p-6 flex flex-col relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 py-1.5 text-center text-xs font-medium bg-gradient-to-r from-pink-500/90 to-purple-500/90 text-white">
                Early Adopters Discount - 50% Off
              </div>
              <div className="pt-6 flex items-center gap-2 mb-2">
                <Layers className="w-5 h-5 text-indigo-400" />
                <h3 className="text-lg font-semibold text-white">ADVANCED</h3>
              </div>
              <p className="text-sm text-slate-400 mb-4">Advanced plan for growing teams</p>
              <div className="mb-2 flex items-baseline gap-2 flex-wrap">
                <span className="text-3xl font-bold text-white">$100</span>
                <span className="text-slate-400">/month</span>
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-pink-500/80 text-white">-50%</span>
              </div>
              <p className="text-xs text-slate-500 line-through mb-4">$199/month</p>
              <p className="text-xs text-slate-500 mb-4">Billed monthly</p>
              <ul className="space-y-3 flex-1 mb-6">
                {['20,000+ credits per month', 'Unlimited file exports', 'Unlimited uploads and file storage', '5 concurrent tasks', 'Priority support'].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                    <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button type="button" className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition border border-indigo-500/50">
                Start free trial
              </button>
            </div>

            {/* Pro Tier */}
            <div className="rounded-2xl border border-white/10 bg-codeRepo-surface/80 p-6 flex flex-col relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 py-1.5 text-center text-xs font-medium bg-gradient-to-r from-pink-500/90 to-purple-500/90 text-white">
                Early Adopters Discount - 50% Off
              </div>
              <div className="pt-6 flex items-center gap-2 mb-2">
                <Crown className="w-5 h-5 text-amber-400" />
                <h3 className="text-lg font-semibold text-white">Pro Tier</h3>
              </div>
              <p className="text-sm text-slate-400 mb-4">Professional plan with high monthly limits</p>
              <div className="mb-2 flex items-baseline gap-2 flex-wrap">
                <span className="text-3xl font-bold text-white">$250</span>
                <span className="text-slate-400">/month</span>
                <span className="px-2 py-0.5 rounded text-xs font-medium bg-pink-500/80 text-white">-50%</span>
              </div>
              <p className="text-xs text-slate-500 line-through mb-4">$499/month</p>
              <p className="text-xs text-slate-500 mb-4">Billed monthly - First month only</p>
              <ul className="space-y-3 flex-1 mb-6">
                {['Unlimited credits per month', 'Unlimited file exports', 'Unlimited uploads and file storage', '5 concurrent tasks'].map((f) => (
                  <li key={f} className="flex items-center gap-2 text-sm text-slate-300">
                    <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                    {f}
                  </li>
                ))}
              </ul>
              <button type="button" className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition border border-indigo-500/50">
                Start free trial
              </button>
            </div>
          </div>
        </div>
      </section>

      <section id="about-us" className="relative py-20 md:py-28 bg-codeRepo-dark">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-center tracking-tight text-white mb-8">About Us</h2>
          <p className="text-lg text-slate-300 leading-relaxed mb-6">
            We are building an advanced repository intelligence platform designed to transform raw codebases into structured architectural knowledge.
          </p>
          <p className="text-lg text-slate-300 leading-relaxed mb-8">
            Modern software systems are complex. Understanding execution flow, dependencies, and architectural boundaries across multiple files and frameworks is time-consuming and error-prone. Our platform automates this process through deterministic static analysis combined with local large language models.
          </p>
          <p className="text-slate-400 mb-3">Instead of summarizing code, we perform structural analysis:</p>
          <ul className="space-y-2 mb-12 list-none">
            {[
              'Entry-point detection across languages and frameworks',
              'Abstract syntax tree (AST)–based symbol extraction',
              'Cross-file call graph construction',
              'Dependency and cycle detection',
              'Architectural zone inference',
              'Centrality and orchestration analysis',
            ].map((item) => (
              <li key={item} className="flex items-start gap-2 text-slate-300">
                <span className="text-indigo-400 mt-1.5 shrink-0">•</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <h3 className="text-2xl md:text-3xl font-bold text-center tracking-tight text-white mb-10">Meet our team</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-8 justify-items-center">
            {/* Placeholder: team photos and roles to be added later */}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-codeRepo-dark py-8 md:py-10">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-slate-400 text-sm">© {new Date().getFullYear()} Code-Repo. All rights reserved.</p>
          <div className="flex items-center gap-6 text-sm">
            <a href="/#application" className="text-slate-400 hover:text-white transition">Application</a>
            <a href="/#pricing" className="text-slate-400 hover:text-white transition">Pricing</a>
            <a href="/#about-us" className="text-slate-400 hover:text-white transition">About us</a>
          </div>
        </div>
      </footer>
    </div>
  )
}
