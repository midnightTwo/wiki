import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, createContext } from 'react'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'

export const AuthContext = createContext()
export const DOMAIN = 'komarnitsky.wiki'

export default function App() {
  const [isAuth, setIsAuth] = useState(false)

  const login = () => setIsAuth(true)

  const logout = async () => {
    await fetch('/api/logout', { method: 'POST' }).catch(() => {})
    setIsAuth(false)
  }

  return (
    <AuthContext.Provider value={{ isAuth, login, logout }}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={isAuth ? <Navigate to="/admin" /> : <Login />} />
          <Route path="/admin" element={isAuth ? <Dashboard /> : <Navigate to="/" />} />
          <Route path="/admin/settings" element={isAuth ? <Settings /> : <Navigate to="/" />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </BrowserRouter>
    </AuthContext.Provider>
  )
}
