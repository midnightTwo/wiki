import { useState, useEffect } from 'react'

const API = '/api'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`${API}/me`).then(r => r.ok ? r.json() : null)
      .then(data => { if (data) setUser(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div className="loader">Loading...</div>
  if (!user) return <Login onLogin={setUser} />
  if (user.is_admin) return <Admin user={user} onLogout={() => { fetch(`${API}/logout`, {method:'POST'}); setUser(null) }} />
  return <Inbox user={user} onLogout={() => { fetch(`${API}/logout`, {method:'POST'}); setUser(null) }} />
}

// ==================== LOGIN ====================
function Login({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const r = await fetch(`${API}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      const data = await r.json()
      if (!r.ok) { setError(data.error || 'Login failed'); setLoading(false); return }
      onLogin(data)
    } catch { setError('Connection error'); setLoading(false) }
  }

  return (
    <div className="login-wrap">
      <div className="login-bg" />
      <form className="login-card" onSubmit={submit}>
        <div className="login-logo">KMR MAIL</div>
        <div className="login-subtitle">Private Mail Server</div>
        {error && <div className="error-msg">{error}</div>}
        <input type="text" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} autoFocus />
        <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} />
        <button type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign In'}</button>
      </form>
    </div>
  )
}

// ==================== INBOX (regular user) ====================
function Inbox({ user, onLogout }) {
  const [messages, setMessages] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadMail = (silent) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    fetch(`${API}/mail`).then(r => r.json())
      .then(data => { setMessages(data.messages || []); setLoading(false); setRefreshing(false) })
      .catch(() => { setLoading(false); setRefreshing(false) })
  }

  useEffect(() => {
    loadMail(false)
    const timer = setInterval(() => loadMail(true), 30000)
    return () => clearInterval(timer)
  }, [])

  const openMail = async (msg) => {
    setSelected(msg.id)
    setDetail(null)
    const r = await fetch(`${API}/mail/${msg.id}`)
    const data = await r.json()
    setDetail(data)
  }

  const deleteMail = async (e, msg) => {
    e.stopPropagation()
    const pin = prompt('Enter PIN to delete:')
    if (pin !== '228') { if (pin !== null) alert('Wrong PIN'); return }
    await fetch(`${API}/mail/${msg.id}`, { method: 'DELETE' })
    setMessages(prev => prev.filter(m => m.id !== msg.id))
    if (selected === msg.id) { setSelected(null); setDetail(null) }
  }

  return (
    <div className="app-wrap">
      <header>
        <span className="logo">KMR MAIL</span>
        <span className="user-info">{user.email}</span>
        <button className="logout-btn" onClick={onLogout}>Logout</button>
      </header>
      <div className="inbox-layout">
        <div className="mail-list">
          <div className="mail-list-header">
            <span>Inbox</span>
            <button className="refresh-btn" onClick={() => loadMail(true)} disabled={refreshing}>{refreshing ? '⟳' : '↻'} Refresh</button>
          </div>
          {loading ? <div className="empty">Loading...</div> :
           messages.length === 0 ? <div className="empty">No messages</div> :
           messages.map(m => (
            <div key={m.id} className={`mail-item ${selected === m.id ? 'active' : ''} ${!m.seen ? 'unread' : ''} ${m.spam ? 'spam' : ''}`} onClick={() => openMail(m)}>
              <div className="mail-from">{m.from.split('<')[0].trim() || m.from}{m.spam && <span className="spam-tag">SPAM</span>}</div>
              <div className="mail-subject">{m.subject}</div>
              <div className="mail-date">{m.date}<button className="del-mail-btn" onClick={(e) => deleteMail(e, m)}>✕</button></div>
            </div>
          ))}
        </div>
        <div className="mail-view">
          {!detail ? <div className="empty">Select a message</div> : (
            <div className="mail-detail">
              <h2>{detail.subject}</h2>
              <div className="mail-meta">
                <span>From: {detail.from}</span>
                <span>Date: {detail.date}</span>
              </div>
              {detail.body_type === 'html' ?
                <iframe className="mail-body-frame" srcDoc={detail.body} sandbox="allow-same-origin" /> :
                <pre className="mail-body-text">{detail.body}</pre>
              }
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ==================== ADMIN ====================
function Admin({ user, onLogout }) {
  const [tab, setTab] = useState('mail')

  return (
    <div className="app-wrap">
      <header>
        <span className="logo">KMR MAIL</span>
        <nav className="tabs">
          <button className={tab === 'mail' ? 'active' : ''} onClick={() => setTab('mail')}>My Mail</button>
          <button className={tab === 'accounts' ? 'active' : ''} onClick={() => setTab('accounts')}>Accounts</button>
        </nav>
        <span className="user-info">admin</span>
        <button className="logout-btn" onClick={onLogout}>Logout</button>
      </header>
      {tab === 'mail' ? <AdminMail user={user} /> : <AccountManager />}
    </div>
  )
}

function AdminMail({ user }) {
  const [messages, setMessages] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const loadMail = (silent) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    fetch(`${API}/mail`).then(r => r.json())
      .then(data => { setMessages(data.messages || []); setLoading(false); setRefreshing(false) })
      .catch(() => { setLoading(false); setRefreshing(false) })
  }

  useEffect(() => {
    loadMail(false)
    const timer = setInterval(() => loadMail(true), 30000)
    return () => clearInterval(timer)
  }, [])

  const openMail = async (msg) => {
    setSelected(msg.id)
    setDetail(null)
    const r = await fetch(`${API}/mail/${msg.id}`)
    const data = await r.json()
    setDetail(data)
  }

  const deleteMail = async (e, msg) => {
    e.stopPropagation()
    const pin = prompt('Enter PIN to delete:')
    if (pin !== '228') { if (pin !== null) alert('Wrong PIN'); return }
    await fetch(`${API}/mail/${msg.id}`, { method: 'DELETE' })
    setMessages(prev => prev.filter(m => m.id !== msg.id))
    if (selected === msg.id) { setSelected(null); setDetail(null) }
  }

  return (
    <div className="inbox-layout">
      <div className="mail-list">
        <div className="mail-list-header">
          <span>Admin Inbox</span>
          <button className="refresh-btn" onClick={() => loadMail(true)} disabled={refreshing}>{refreshing ? '⟳' : '↻'} Refresh</button>
        </div>
        {loading ? <div className="empty">Loading...</div> :
         messages.length === 0 ? <div className="empty">No messages</div> :
         messages.map(m => (
          <div key={m.id} className={`mail-item ${selected === m.id ? 'active' : ''} ${!m.seen ? 'unread' : ''} ${m.spam ? 'spam' : ''}`} onClick={() => openMail(m)}>
            <div className="mail-from">{m.from.split('<')[0].trim() || m.from}{m.spam && <span className="spam-tag">SPAM</span>}</div>
            <div className="mail-subject">{m.subject}</div>
            <div className="mail-date">{m.date}<button className="del-mail-btn" onClick={(e) => deleteMail(e, m)}>✕</button></div>
          </div>
        ))}
      </div>
      <div className="mail-view">
        {!detail ? <div className="empty">Select a message</div> : (
          <div className="mail-detail">
            <h2>{detail.subject}</h2>
            <div className="mail-meta">
              <span>From: {detail.from}</span>
              <span>Date: {detail.date}</span>
            </div>
            {detail.body_type === 'html' ?
              <iframe className="mail-body-frame" srcDoc={detail.body} sandbox="allow-same-origin" /> :
              <pre className="mail-body-text">{detail.body}</pre>
            }
          </div>
        )}
      </div>
    </div>
  )
}

function AccountManager() {
  const [accounts, setAccounts] = useState([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [genCount, setGenCount] = useState(1)
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState('')

  const load = () => {
    fetch(`${API}/admin/accounts`).then(r => r.json())
      .then(data => setAccounts(data.accounts || []))
  }

  useEffect(load, [])

  const create = async (e) => {
    e.preventDefault()
    if (!username || !password || password.length < 6) { setMsg('Username + password (6+ chars)'); return }
    setLoading(true)
    const r = await fetch(`${API}/admin/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    const data = await r.json()
    if (!r.ok) { setMsg(data.error); setLoading(false); return }
    setMsg(`Created: ${data.email}`)
    setUsername('')
    setPassword('')
    setLoading(false)
    load()
  }

  const generate = async () => {
    setLoading(true)
    const r = await fetch(`${API}/admin/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ count: genCount })
    })
    const data = await r.json()
    setMsg(`Generated ${data.created.length} accounts`)
    setLoading(false)
    load()
  }

  const del = async (email) => {
    if (!confirm(`Delete ${email}?`)) return
    await fetch(`${API}/admin/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    })
    load()
  }

  const copy = (text) => {
    navigator.clipboard.writeText(text)
    setCopied(text)
    setTimeout(() => setCopied(''), 2000)
  }

  const copyAll = () => {
    const text = accounts.map(a => `${a.email}:${a.password}`).join('\n')
    navigator.clipboard.writeText(text)
    setCopied('all')
    setTimeout(() => setCopied(''), 2000)
  }

  return (
    <div className="accounts-wrap">
      <div className="accounts-panel">
        <h3>Create Account</h3>
        <form onSubmit={create} className="create-form">
          <div className="input-row">
            <input placeholder="username" value={username} onChange={e => setUsername(e.target.value)} />
            <span className="domain">@kmr-mail.online</span>
          </div>
          <input type="password" placeholder="Password (6+ chars)" value={password} onChange={e => setPassword(e.target.value)} />
          <button type="submit" disabled={loading}>Create</button>
        </form>

        <h3>Generate Random</h3>
        <div className="gen-row">
          <input type="number" min="1" max="50" value={genCount} onChange={e => setGenCount(e.target.value)} />
          <button onClick={generate} disabled={loading}>Generate</button>
        </div>

        {msg && <div className="status-msg">{msg}</div>}
      </div>

      <div className="accounts-list">
        <div className="accounts-header">
          <h3>Accounts ({accounts.length})</h3>
          {accounts.length > 0 && <button className="copy-all-btn" onClick={copyAll}>{copied === 'all' ? 'Copied!' : 'Copy All'}</button>}
        </div>
        {accounts.map(a => (
          <div key={a.email} className="account-item">
            <div className="account-info">
              <span className="account-email">{a.email}</span>
              <span className="account-pass">{a.password}</span>
            </div>
            <div className="account-actions">
              <button className="copy-btn" onClick={() => copy(`${a.email}:${a.password}`)}>{copied === `${a.email}:${a.password}` ? 'OK' : 'Copy'}</button>
              <button className="del-btn" onClick={() => del(a.email)}>Del</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App
