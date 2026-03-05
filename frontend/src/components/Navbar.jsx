import { useContext } from 'react'
import { Link } from 'react-router-dom'
import { AuthContext } from '../App'
import { Icon } from './Icons'

export default function Navbar({ active }) {
  const { isAuth, logout } = useContext(AuthContext)

  if (!isAuth) return null

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link to="/admin" className="navbar-brand">
          <div className="navbar-logo"><Icon name="mail" size={18} /></div>
          <span>Komarnitsky <span style={{ color: 'var(--accent)' }}>Mail</span></span>
        </Link>

        <div className="navbar-nav">
          <Link to="/admin" className={`nav-link ${active === 'dashboard' ? 'active' : ''}`}>
            <Icon name="chart" size={16} /> <span>Дашборд</span>
          </Link>
          <Link to="/admin/settings" className={`nav-link ${active === 'settings' ? 'active' : ''}`}>
            <Icon name="settings" size={16} /> <span>Настройки</span>
          </Link>
          <button onClick={logout} className="btn btn-ghost btn-sm">
            <Icon name="logout" size={16} /> Выйти
          </button>
        </div>
      </div>
    </nav>
  )
}
