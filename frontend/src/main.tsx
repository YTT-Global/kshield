import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import './index.css'
import App from './App.tsx'
import { Landing } from './components/Landing.tsx'
import { ThemeProvider } from './context/ThemeContext.tsx'

// Handles the 404 → sessionStorage redirect from public/404.html (GitHub Pages SPA routing)
function SpaRedirectHandler() {
  const navigate = useNavigate()
  useEffect(() => {
    const redirect = sessionStorage.getItem('spa-redirect')
    if (redirect) {
      sessionStorage.removeItem('spa-redirect')
      navigate(redirect, { replace: true })
    }
  }, [navigate])
  return null
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <BrowserRouter basename={import.meta.env.BASE_URL}>
        <SpaRedirectHandler />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/kshield-dashboard/*" element={<App />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
