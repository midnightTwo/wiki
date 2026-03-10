import { useState, useEffect } from 'react'

const API = '/api'

function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text)
  }
  const ta = document.createElement('textarea')
  ta.value = text
  ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px'
  document.body.appendChild(ta)
  ta.select()
  document.execCommand('copy')
  document.body.removeChild(ta)
  return Promise.resolve()
}

function wrapHtml(html) {
  const baseTag = '<base target="_blank">'
  // If already a full HTML document, inject base tag only
  if (/<html[\s>]/i.test(html)) {
    if (/<head[\s>]/i.test(html)) {
      return html.replace(/<head([^>]*)>/i, '<head$1>' + baseTag)
    }
    return html.replace(/<html([^>]*)>/i, '<html$1><head>' + baseTag + '</head>')
  }
  // Fragment — wrap with basic styles
  return `<!DOCTYPE html><html><head><meta charset="utf-8">${baseTag}<style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:14px;line-height:1.6;color:#222;padding:12px;margin:0;word-break:break-word}a{color:#1a73e8}img{max-width:100%;height:auto}pre,code{white-space:pre-wrap;word-break:break-all}table{max-width:100%;border-collapse:collapse}td,th{padding:4px 8px}</style></head><body>${html}</body></html>`
}

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
                <iframe className="mail-body-frame" srcDoc={wrapHtml(detail.body)} sandbox="allow-popups allow-popups-to-escape-sandbox" /> :
                <pre className="mail-body-text">{detail.body}</pre>
              }
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ==================== ADMIN ======================================
function Admin({ user, onLogout }) {
  const [tab, setTab] = useState('mail')
  const [accounts, setAccounts] = useState([])

  const loadAccounts = () => {
    fetch(`${API}/admin/accounts`).then(r => r.json())
      .then(data => setAccounts(data.accounts || []))
  }
  useEffect(loadAccounts, [])

  return (
    <div className="app-wrap">
      <header>
        <span className="logo">KMR MAIL</span>
        <nav className="tabs">
          <button className={tab === 'mail' ? 'active' : ''} onClick={() => setTab('mail')}>Mail</button>
          <button className={tab === 'accounts' ? 'active' : ''} onClick={() => setTab('accounts')}>Accounts</button>
        </nav>
        <span className="user-info">admin</span>
        <button className="logout-btn" onClick={onLogout}>Logout</button>
      </header>
      {tab === 'mail' ? <AdminMail user={user} accounts={accounts} /> : <AccountManager accounts={accounts} setAccounts={setAccounts} reload={loadAccounts} />}
    </div>
  )
}

function AdminMail({ user, accounts }) {
  const [currentAccount, setCurrentAccount] = useState(user.email)
  const [messages, setMessages] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [search, setSearch] = useState('')
  const [accSearch, setAccSearch] = useState('')
  const [showAccList, setShowAccList] = useState(false)

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
  const filteredAccounts = allAccounts.filter(a => !accSearch || a.toLowerCase().includes(accSearch.toLowerCase()))
  const curAcc = accounts.find(a => a.email === currentAccount)
  const curTags = curAcc?.tags || {}
  const activeTags = TAGS.filter(t => curTags[t.key])

  return (
    <div className="inbox-layout">
      <div className="mail-list">
        <div className="mail-list-header">
          <div className="account-switcher">
            <button className="account-switcher-btn" onClick={() => setShowAccList(!showAccList)}>
              <span className="account-switcher-email">{currentAccount === user.email ? '✦ admin' : currentAccount.split('@')[0]}</span>
              <span className="account-switcher-domain">@{currentAccount.split('@')[1]}</span>
              <span className="account-switcher-arrow">{showAccList ? '▲' : '▼'}</span>
            </button>
            {showAccList && (
              <div className="account-dropdown">
                <input className="account-dropdown-search" placeholder="Search accounts..." value={accSearch} onChange={e => setAccSearch(e.target.value)} autoFocus />
                <div className="account-dropdown-list">
                  {filteredAccounts.map(a => {
                    const acc = accounts.find(x => x.email === a)
                    const tags = acc?.tags || {}
                    const active = TAGS.filter(t => tags[t.key])
                    return (
                      <div key={a} className={`account-dropdown-item ${a === currentAccount ? 'active' : ''}`} onClick={() => { switchAccount(a); setShowAccList(false); setAccSearch('') }}>
                        <span className="account-dropdown-name">{a === user.email ? '✦ admin' : a.split('@')[0]}</span>
                        <span className="account-dropdown-domain">@{a.split('@')[1]}</span>
                        {active.length > 0 && <span className="account-dropdown-tags">{active.map(t => t.label.charAt(0)).join('')}</span>}
                      </div>
                    )
                  })}
                  {filteredAccounts.length === 0 && <div className="account-dropdown-empty">No accounts found</div>}
                </div>
              </div>
            )}
          </div>
          <button className="refresh-btn" onClick={() => loadMail(true)} disabled={refreshing}>{refreshing ? '⟳' : '↻'}</button>
        </div>
        {curAcc && activeTags.length > 0 && (
          <div className="mail-account-tags">
            {activeTags.map(t => (
              <span key={t.key} className={`mini-tag tag-${curTags[t.key]}`}>
                <TagIcon name={t.key} />{t.label}
              </span>
            ))}
          </div>
        )}
        <div className="mail-search-bar">
          <input placeholder="Search emails..." value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        {loading ? <div className="empty">Loading...</div> :
         messages.length === 0 ? <div className="empty">No messages</div> :
         messages.filter(m => !search || m.subject?.toLowerCase().includes(search.toLowerCase()) || m.from?.toLowerCase().includes(search.toLowerCase())).map(m => (
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
              <iframe className="mail-body-frame" srcDoc={wrapHtml(detail.body)} sandbox="allow-popups allow-popups-to-escape-sandbox" /> :
              <pre className="mail-body-text">{detail.body}</pre>
            }
          </div>
        )}
      </div>
    </div>
  )
}

// ==================== TAG ICONS (SVG) ====================
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

function AccountManager({ accounts, setAccounts, reload }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [genCount, setGenCount] = useState(5)
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState('')
  const [selected, setSelected] = useState(new Set())
  const [search, setSearch] = useState('')
  const [filterTag, setFilterTag] = useState('')
  const [domains, setDomains] = useState(['kmr-mail.online'])
  const [domain, setDomain] = useState('kmr-mail.online')
  const [jobProgress, setJobProgress] = useState(null) // {done, total, status}

  useEffect(() => {
    fetch(`${API}/domains`).then(r => r.json()).then(d => {
      if (d.domains && d.domains.length) {
        setDomains(d.domains)
        setDomain(d.domains[0])
      }
    }).catch(() => {})
  }, [])

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
      body: JSON.stringify({ username, password, domain })
    })
    const data = await r.json()
    if (!r.ok) { setMsg(data.error); setLoading(false); return }
    setMsg(`Created: ${data.email}`)
    setUsername('')
    setPassword('')
    setLoading(false)
    reload()
  }

  const generate = async () => {
    setLoading(true)
    setMsg('')
    try {
      const r = await fetch(`${API}/admin/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count: genCount, domain })
      })
      const data = await r.json()
      if (data.job_id) {
        // Background job — poll for progress
        setJobProgress({ done: 0, total: genCount, status: 'running' })
        const pollInterval = setInterval(async () => {
          try {
            const jr = await fetch(`${API}/admin/job/${data.job_id}`)
            const job = await jr.json()
            setJobProgress({ done: job.done, total: job.total, status: job.status })
            if (job.status === 'done') {
              clearInterval(pollInterval)
              setJobProgress(null)
              setMsg(`Generated ${job.created.length} accounts${job.errors ? ` (${job.errors} errors)` : ''}`)
              setLoading(false)
              reload()
            }
          } catch {
            clearInterval(pollInterval)
            setJobProgress(null)
            setLoading(false)
            reload()
          }
        }, 1500)
      } else {
        setMsg(`Generated ${data.created?.length || 0} accounts`)
        setLoading(false)
        reload()
      }
    } catch {
      setMsg('Connection error')
      setLoading(false)
    }
  }

  const del = async (email) => {
    if (!confirm(`Delete ${email}?`)) return
    await fetch(`${API}/admin/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    })
    reload()
  }

  const deleteSelected = async () => {
    if (!selected.size) return
    if (!confirm(`Delete ${selected.size} selected accounts?`)) return
    setLoading(true)
    setMsg('')
    await fetch(`${API}/admin/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ emails: Array.from(selected) })
    })
    setSelected(new Set())
    setMsg(`Deleted ${selected.size} accounts`)
    setLoading(false)
    reload()
  }

  const copy = (text, id) => {
    copyText(text)
    setCopied(id)
    setTimeout(() => setCopied(''), 1500)
  }

  const toggleSelect = (email) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(email)) next.delete(email)
      else next.add(email)
      return next
    })
  }

  const selectAll = () => {
    if (selected.size === filtered.length) setSelected(new Set())
    else setSelected(new Set(filtered.map(a => a.email)))
  }

  const copySelected = () => {
    const text = accounts.filter(a => selected.has(a.email)).map(a => `${a.email}:${a.password}`).join('\n')
    copyText(text)
    setCopied('selected')
    setTimeout(() => setCopied(''), 2000)
  }

  const filtered = accounts.filter(a => {
    if (search && !a.email.toLowerCase().includes(search.toLowerCase())) return false
    if (filterTag && !(a.tags || {})[filterTag]) return false
    return true
  })

  return (
    <div className="accounts-wrap">
      <div className="accounts-panel">
        <h3>Create Account</h3>
        <form onSubmit={create} className="create-form">
          <div className="domain-picker">
            {domains.map(d => (
              <button type="button" key={d} className={`domain-btn ${domain === d ? 'active' : ''}`} onClick={() => setDomain(d)}>{d}</button>
            ))}
          </div>
          <div className="input-row">
            <input placeholder="username" value={username} onChange={e => setUsername(e.target.value)} />
            <span className="domain">@{domain}</span>
          </div>
          <input type="password" placeholder="Password (6+ chars)" value={password} onChange={e => setPassword(e.target.value)} />
          <button type="submit" disabled={loading}>Create</button>
        </form>

        <h3>Generate Random</h3>
        <div className="gen-section">
          <div className="domain-picker">
            {domains.map(d => (
              <button type="button" key={d} className={`domain-btn ${domain === d ? 'active' : ''}`} onClick={() => setDomain(d)}>{d}</button>
            ))}
          </div>
          <div className="gen-row">
            <label className="gen-label">Count:</label>
            <div className="gen-count-wrap">
              <button type="button" className="gen-count-btn" onClick={() => setGenCount(Math.max(1, Number(genCount) - 1))}>−</button>
              <input type="number" min="1" max="200" value={genCount} onChange={e => setGenCount(e.target.value)} />
              <button type="button" className="gen-count-btn" onClick={() => setGenCount(Math.min(200, Number(genCount) + 1))}>+</button>
            </div>
            <button className="gen-btn" onClick={generate} disabled={loading}>
              {loading && jobProgress ? `${jobProgress.done}/${jobProgress.total}...` : loading ? 'Working...' : 'Generate'}
            </button>
          </div>
          {jobProgress && (
            <div className="job-progress">
              <div className="job-progress-bar" style={{width: `${Math.round(jobProgress.done / jobProgress.total * 100)}%`}} />
              <span className="job-progress-text">{jobProgress.done}/{jobProgress.total} ({Math.round(jobProgress.done / jobProgress.total * 100)}%)</span>
            </div>
          )}
        </div>

        {msg && <div className="status-msg">{msg}</div>}

        {selected.size > 0 && (
          <div className="selection-actions">
            <h3>Selected ({selected.size})</h3>
            <button className="copy-selected-btn" onClick={copySelected}>
              {copied === 'selected' ? 'Copied!' : `Copy ${selected.size} accounts`}
            </button>
            <button className="del-selected-btn" onClick={deleteSelected}>
              Delete {selected.size} selected
            </button>
            <button className="clear-sel-btn" onClick={() => setSelected(new Set())}>Clear selection</button>
          </div>
        )}
      </div>

      <div className="accounts-list">
        <div className="accounts-toolbar">
          <div className="accounts-toolbar-top">
            <h3>Accounts ({filtered.length}{filtered.length !== accounts.length ? `/${accounts.length}` : ''})</h3>
            <div className="toolbar-btns">
              {filtered.length > 0 && <button className="toolbar-btn" onClick={selectAll}>{selected.size === filtered.length ? 'Deselect' : 'Select All'}</button>}
              {accounts.length > 0 && <button className="toolbar-btn" onClick={() => copy(accounts.map(a => `${a.email}:${a.password}`).join('\n'), 'all')}>{copied === 'all' ? 'Copied!' : 'Copy All'}</button>}
            </div>
          </div>
          <div className="accounts-toolbar-bottom">
            <input className="search-input" placeholder="Search accounts..." value={search} onChange={e => setSearch(e.target.value)} />
            <select className="filter-tag-select" value={filterTag} onChange={e => setFilterTag(e.target.value)}>
              <option value="">All tags</option>
              {TAGS.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}
            </select>
          </div>
        </div>
        {filtered.map(a => (
          <div key={a.email} className={`account-card ${selected.has(a.email) ? 'selected' : ''}`}>
            <div className="account-card-header">
              <div className="account-card-check" onClick={() => toggleSelect(a.email)}>
                <div className={`checkbox ${selected.has(a.email) ? 'checked' : ''}`}>{selected.has(a.email) ? '✓' : ''}</div>
              </div>
              <div className="account-card-info">
                <span className="account-email">{a.email}</span>
                <span className="account-pass">{a.password}</span>
              </div>
              <div className="account-card-actions">
                <button className="act-btn" onClick={() => copy(a.email, 'e:' + a.email)} title="Copy email">
                  {copied === 'e:' + a.email ? '✓' : 'Email'}
                </button>
                <button className="act-btn" onClick={() => copy(a.password, 'p:' + a.email)} title="Copy password">
                  {copied === 'p:' + a.email ? '✓' : 'Pass'}
                </button>
                <button className="act-btn accent" onClick={() => copy(`${a.email}:${a.password}`, 'f:' + a.email)} title="Copy email:password">
                  {copied === 'f:' + a.email ? '✓' : 'Full'}
                </button>
                <button className="act-btn danger" onClick={() => del(a.email)} title="Delete">Del</button>
              </div>
            </div>
            <div className="account-card-tags">
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
        ))}
      </div>
    </div>
  )
}

export default App
