import { useState, useContext, useEffect, useRef } from 'react'
import { AuthContext, DOMAIN } from '../App'

export default function Login() {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPw, setShowPw] = useState(false)
  const { login } = useContext(AuthContext)
  const bgRef = useRef(null)

  // Parallax
  useEffect(() => {
    const handleMouse = (e) => {
      if (!bgRef.current) return
      const x = (e.clientX / window.innerWidth - 0.5) * 30
      const y = (e.clientY / window.innerHeight - 0.5) * 30
      const layers = bgRef.current.querySelectorAll('.parallax-layer')
      layers.forEach((layer, i) => {
        const depth = (i + 1) * 0.4
        layer.style.transform = `translate(${x * depth}px, ${y * depth}px)`
      })
    }
    window.addEventListener('mousemove', handleMouse)
    return () => window.removeEventListener('mousemove', handleMouse)
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
      })
      const data = await res.json()

      if (data.success) {
        login()
      } else {
        setError(data.error || 'Неверный пароль')
        setPassword('')
      }
    } catch {
      setError('Ошибка подключения к серверу')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-scene">
      {/* Parallax Background */}
      <div className="parallax-bg" ref={bgRef}>
        <div className="parallax-layer">
          <div className="neon-grid"></div>
        </div>
        <div className="parallax-layer">
          <div className="neon-orb neon-orb-1"></div>
          <div className="neon-orb neon-orb-2"></div>
        </div>
        <div className="parallax-layer">
          <div className="neon-orb neon-orb-3"></div>
          <div className="neon-line neon-line-1"></div>
          <div className="neon-line neon-line-2"></div>
        </div>
        <div className="parallax-layer">
          <div className="neon-ring neon-ring-1"></div>
          <div className="neon-ring neon-ring-2"></div>
        </div>
      </div>

      {/* Login Card */}
      <div className="login-container">
        <div className="login-card animate-in">
          <div className="login-glow"></div>
          
          <div className="login-header">
            <div className="login-logo">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="4" width="20" height="16" rx="2"/>
                <path d="M22 7l-10 7L2 7"/>
              </svg>
            </div>
            <h1>{DOMAIN}</h1>
            <p>Панель управления почтой</p>
          </div>

          {error && (
            <div className="login-error animate-in">
              <span>✕</span> {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="login-field">
              <input
                type={showPw ? 'text' : 'password'}
                className="login-input"
                placeholder="Пароль администратора"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoFocus
              />
              <button
                type="button"
                className="login-eye"
                onClick={() => setShowPw(!showPw)}
              >
                {showPw ? '◉' : '◎'}
              </button>
            </div>

            <button
              type="submit"
              className="login-btn"
              disabled={loading}
            >
              {loading ? <span className="spinner" /> : 'Войти'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
