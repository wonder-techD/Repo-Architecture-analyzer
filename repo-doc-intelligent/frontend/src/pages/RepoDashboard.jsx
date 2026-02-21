import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { FileDown, ArrowLeft, MessageCircle, X, Sun, Moon } from 'lucide-react'
import axios from 'axios'
import TOCSidebar, { extractHeadings } from '../components/TOCSidebar'
import MarkdownContent from '../components/MarkdownContent'
import ChatPanel from '../components/ChatPanel'

const API_BASE = import.meta.env.VITE_API_URL || ''

export default function RepoDashboard() {
  const { id: jobId } = useParams()
  const [content, setContent] = useState(null)
  const [error, setError] = useState('')
  const [chatOpen, setChatOpen] = useState(false)
  const headings = content?.markdown ? extractHeadings(content.markdown) : []

  useEffect(() => {
    if (!jobId) return
    let cancelled = false
    axios
      .get(`${API_BASE}/content/${jobId}`)
      .then(({ data }) => {
        if (!cancelled) setContent(data)
      })
      .catch((err) => {
        if (!cancelled) setError(err.response?.data?.detail || err.message || 'Failed to load.')
      })
    return () => { cancelled = true }
  }, [jobId])

  if (error) {
    return (
      <div className="min-h-screen bg-codeRepo-dark flex flex-col">
        <DashboardHeader />
        <div className="flex-1 flex items-center justify-center p-6">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="rounded-xl bg-codeRepo-surface border border-white/10 p-8 max-w-md text-center"
          >
            <p className="text-red-400">{error}</p>
            <Link
              to="/"
              className="mt-4 inline-flex items-center gap-2 text-indigo-400 hover:text-indigo-300 transition"
            >
              <ArrowLeft className="w-4 h-4" />
              New analysis
            </Link>
          </motion.div>
        </div>
      </div>
    )
  }

  if (!content) {
    return (
      <div className="min-h-screen bg-codeRepo-dark flex flex-col">
        <DashboardHeader />
        <div className="flex-1 flex items-center justify-center p-6">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="rounded-xl bg-codeRepo-surface border border-white/10 p-8"
          >
            <p className="text-slate-400">Loading documentation…</p>
            <div className="mt-4 h-1 w-48 bg-white/10 rounded overflow-hidden">
              <motion.div
                className="h-full bg-indigo-500"
                initial={{ width: '0%' }}
                animate={{ width: '40%' }}
                transition={{ repeat: Infinity, duration: 1.2, repeatType: 'reverse' }}
              />
            </div>
          </motion.div>
        </div>
      </div>
    )
  }

  const downloadUrl = `${API_BASE}/download/${jobId}`

  return (
    <div className="min-h-screen bg-codeRepo-dark text-white flex flex-col">
      <DashboardHeader />
      <div className="flex-1 flex flex-col lg:flex-row gap-6 p-6 max-w-[1600px] mx-auto w-full min-h-0">
        <div className="lg:w-56 shrink-0">
          <TOCSidebar headings={headings} />
        </div>
        <main className="flex-1 min-w-0 overflow-y-auto">
          <div className="max-w-3xl mx-auto">
            <div className="flex flex-wrap items-center gap-3 mb-6">
              <Link
                to="/"
                className="inline-flex items-center gap-2 text-sm text-slate-400 hover:text-white transition"
              >
                <ArrowLeft className="w-4 h-4" />
                New analysis
              </Link>
              <a
                href={downloadUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-codeRepo-surface px-4 py-2 text-sm font-medium text-white hover:bg-white/5 transition"
              >
                <FileDown className="w-4 h-4" />
                Download PDF
              </a>
            </div>
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
              className="rounded-xl border border-white/10 bg-codeRepo-surface/50 p-6 lg:p-8"
            >
              <MarkdownContent markdown={content.markdown} />
            </motion.div>
          </div>
        </main>
        <aside className="hidden lg:block w-80 shrink-0 lg:sticky lg:top-20 lg:self-start">
          <ChatPanel jobId={jobId} />
        </aside>
      </div>
      <div className="lg:hidden fixed bottom-6 right-6 z-40">
        <button
          type="button"
          onClick={() => setChatOpen(true)}
          className="w-14 h-14 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 text-white shadow-lg flex items-center justify-center"
        >
          <MessageCircle className="w-6 h-6" />
        </button>
      </div>
      <AnimatePresence>
        {chatOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="lg:hidden fixed inset-0 bg-black/60 z-50"
              onClick={() => setChatOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.2 }}
              className="lg:hidden fixed top-0 right-0 bottom-0 w-full max-w-sm z-50 p-4"
            >
              <div className="h-full relative rounded-xl overflow-hidden">
                <button
                  type="button"
                  onClick={() => setChatOpen(false)}
                  className="absolute top-2 right-2 z-10 p-2 rounded-lg bg-white/10 text-white"
                >
                  <X className="w-5 h-5" />
                </button>
                <ChatPanel jobId={jobId} className="h-full" />
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

function getStoredTheme() {
  try {
    return localStorage.getItem('theme') !== 'light'
  } catch {
    return true
  }
}

const DASHBOARD_NAV_LINKS = [
  { label: 'Application', hash: 'application' },
  { label: 'Core Capabilities', hash: 'core-capabilities' },
  { label: 'Pricing', hash: 'pricing' },
  { label: 'How it works', hash: 'how-it-works' },
  { label: 'About us', hash: 'about-us' },
]

function DashboardHeader() {
  const [isDark, setIsDark] = useState(getStoredTheme)

  useEffect(() => {
    const theme = document.documentElement.getAttribute('data-theme')
    setIsDark(theme !== 'light')
  }, [])

  const setTheme = (dark) => {
    setIsDark(dark)
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    try {
      localStorage.setItem('theme', dark ? 'dark' : 'light')
    } catch {}
  }

  return (
    <header className="sticky top-0 z-50 border-b border-white/5 bg-codeRepo-bg/90 backdrop-blur-md">
      <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
        <Link to="/" className="text-xl font-semibold tracking-tight text-white">
          Code-Repo
        </Link>
        <nav className="hidden md:flex items-center gap-8">
          {DASHBOARD_NAV_LINKS.map(({ label, hash }) => (
            <a
              key={hash}
              href={`/#${hash}`}
              className="text-sm font-bold text-white hover:text-white/90 transition"
            >
              {label}
            </a>
          ))}
          <button
            type="button"
            onClick={() => setTheme(!isDark)}
            className="p-2 rounded-lg text-white hover:bg-white/10 transition focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
          </button>
        </nav>
      </div>
    </header>
  )
}
