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
              <div className="mail-date">{m.date}</div>
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
  const [accounts, setAccounts] = useState([])
  const [currentAccount, setCurrentAccount] = useState(user.email)
  const [messages, setMessages] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetch(`${API}/admin/accounts`).then(r => r.json())
      .then(data => setAccounts(data.accounts || []))
  }, [])

  const loadMail = (silent) => {
    if (!silent) setLoading(true)
    else setRefreshing(true)
    const url = currentAccount === user.email
      ? `${API}/mail`
      : `${API}/admin/mail?account=${encodeURIComponent(currentAccount)}`
    fetch(url).then(r => r.json())
      .then(data => { setMessages(data.messages || []); setLoading(false); setRefreshing(false) })
      .catch(() => { setLoading(false); setRefreshing(false) })
  }

  useEffect(() => {
    loadMail(false)
    const timer = setInterval(() => loadMail(true), 30000)
    return () => clearInterval(timer)
  }, [currentAccount])

  const switchAccount = (acc) => {
    setCurrentAccount(acc)
    setSelected(null)
    setDetail(null)
    setMessages([])
  }

  const openMail = async (msg) => {
    setSelected(msg.id)
    setDetail(null)
    const url = currentAccount === user.email
      ? `${API}/mail/${msg.id}`
      : `${API}/admin/mail/${msg.id}?account=${encodeURIComponent(currentAccount)}`
    const r = await fetch(url)
    const data = await r.json()
    setDetail(data)
  }

  const deleteMail = async (e, msg) => {
    e.stopPropagation()
    if (!confirm('Delete this email?')) return
    const url = currentAccount === user.email
      ? `${API}/mail/${msg.id}`
      : `${API}/admin/mail/${msg.id}?account=${encodeURIComponent(currentAccount)}`
    await fetch(url, { method: 'DELETE' })
    setMessages(prev => prev.filter(m => m.id !== msg.id))
    if (selected === msg.id) { setSelected(null); setDetail(null) }
  }

  const allAccounts = [user.email, ...accounts.map(a => a.email)]

  return (
    <div className="inbox-layout">
      <div className="mail-list">
        <div className="mail-list-header">
          <select className="account-select" value={currentAccount} onChange={e => switchAccount(e.target.value)}>
            {allAccounts.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
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

// ==================== TAG ICONS (SVG) ====================
function TagIcon({ name }) {
  const s = { width: 14, height: 14, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' }
  switch (name) {
    case 'cursor': return <svg {...s}><path d='M4 4l7.07 17 2.51-7.39L21 11.07z'/><path d='M13.58 13.58L21 21'/></svg>
    case 'chatgpt': return <svg {...s}><circle cx='12' cy='12' r='10'/><path d='M12 6v2m0 8v2M6 12h2m8 0h2'/><circle cx='12' cy='12' r='3'/></svg>
    case 'claude': return <svg {...s}><path d='M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20z'/><path d='M8 12h8M12 8v8' stroke='currentColor' strokeWidth='2.5'/></svg>
    case 'copilot': return <svg {...s}><path d='M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5L2 10.3c-.2.5 0 1 .5 1.2l4.5 2 2.5 2.5 2 4.5c.2.5.7.7 1.2.5l3.6-1.7c.4-.2.6-.6.5-1.1z'/></svg>
    case 'midjourney': return <svg {...s}><polygon points='12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2'/></svg>
    case 'other': return <svg {...s}><circle cx='12' cy='12' r='1'/><circle cx='19' cy='12' r='1'/><circle cx='5' cy='12' r='1'/></svg>
    default: return null
  }
}

function AccountManager() {
  const [accounts, setAccounts] = useState([])
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [genCount, setGenCount] = useState(1)
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState('')

  const TAGS = [
    { key: 'cursor', label: 'Cursor AI' },
    { key: 'chatgpt', label: 'ChatGPT' },
    { key: 'claude', label: 'Claude' },
    { key: 'copilot', label: 'Copilot' },
    { key: 'midjourney', label: 'Midjourney' },
    { key: 'other', label: 'Other' },
  ]
  const STATUS_CYCLE = [null, 'wait', 'ok', 'fail']
  const STATUS_DOT = { wait: '●', ok: '●', fail: '●' }

  const load = () => {
    fetch(`${API}/admin/accounts`).then(r => r.json())
      .then(data => setAccounts(data.accounts || []))
  }

  useEffect(load, [])

  const toggleTag = async (email, tagKey, currentTags) => {
    const current = currentTags[tagKey] || null
    const idx = STATUS_CYCLE.indexOf(current)
    const next = STATUS_CYCLE[(idx + 1) % STATUS_CYCLE.length]
    const newTags = { ...currentTags }
    if (next === null) delete newTags[tagKey]
    else newTags[tagKey] = next
    setAccounts(prev => prev.map(a => a.email === email ? { ...a, tags: newTags } : a))
    await fetch(`${API}/admin/tags`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, tags: newTags })
    })
  }

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
              <div className="account-top-row">
                <span className="account-email">{a.email}</span>
                <span className="account-pass">{a.password}</span>
              </div>
              <div className="account-tags">
                {TAGS.map(t => {
                  const status = (a.tags || {})[t.key] || null
                  return (
                    <button
                      key={t.key}
                      className={`tag-chip ${status ? 'tag-' + status : 'tag-off'}`}
                      title={`${t.label}${status ? ' — ' + status : ''}`}
                      onClick={() => toggleTag(a.email, t.key, a.tags || {})}
                    >
                      <TagIcon name={t.key} />
                      <span className="tag-label">{t.label}</span>
                      {status && <span className={`tag-dot tag-dot-${status}`}>{STATUS_DOT[status]}</span>}
                    </button>
                  )
                })}
              </div>
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
