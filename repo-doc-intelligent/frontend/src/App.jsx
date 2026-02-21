import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import LandingPage from './pages/LandingPage'
import RepoDashboard from './pages/RepoDashboard'

export default function App() {
  useEffect(() => {
    try {
      const theme = localStorage.getItem('theme')
      document.documentElement.setAttribute('data-theme', theme === 'light' ? 'light' : 'dark')
    } catch {}
  }, [])

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/dashboard/:id" element={<RepoDashboard />} />
    </Routes>
  )
}
