import { useState, useEffect } from 'react'
import { DOMAIN } from '../App'
import Navbar from '../components/Navbar'
import Modal from '../components/Modal'
import Toast from '../components/Toast'
import { Icon } from '../components/Icons'

const MAX_MAILBOXES = 50

function copyToClipboard(text, showToast) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Скопировано: ' + text)
  }).catch(() => {
    showToast('Ошибка копирования', 'error')
  })
}

export default function Dashboard() {
  const [mailboxes, setMailboxes] = useState([])
  const [aliases, setAliases] = useState([])
  const [activity, setActivity] = useState([])
  const [stats, setStats] = useState({ total_mailboxes: 0, active_mailboxes: 0, total_aliases: 0 })
  const [activeTab, setActiveTab] = useState('mailboxes')
  const [toast, setToast] = useState(null)

  const [showCreateMailbox, setShowCreateMailbox] = useState(false)
  const [showCreateAlias, setShowCreateAlias] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [selectedEmail, setSelectedEmail] = useState('')

  // Created account (to show credentials after creation)
  const [createdAccount, setCreatedAccount] = useState(null)
  // View saved credentials for existing mailbox
  const [viewCredentials, setViewCredentials] = useState(null)

  // Saved passwords in localStorage
  const getSavedPasswords = () => {
    try { return JSON.parse(localStorage.getItem('km_passwords') || '{}') } catch { return {} }
  }
  const savePassword = (email, password) => {
    const saved = getSavedPasswords()
    saved[email] = password
    localStorage.setItem('km_passwords', JSON.stringify(saved))
  }
  const removePassword = (email) => {
    const saved = getSavedPasswords()
    delete saved[email]
    localStorage.setItem('km_passwords', JSON.stringify(saved))
  }

  const [newMailbox, setNewMailbox] = useState({ username: '', password: '', display_name: '' })
  const [newAlias, setNewAlias] = useState({ source: '', destination: '' })
  const [newPassword, setNewPassword] = useState('')

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 3000)
  }

  const fetchData = async () => {
    try {
      const [mbRes, alRes, actRes, stRes] = await Promise.all([
        fetch('/api/mailboxes'),
        fetch('/api/aliases'),
        fetch('/api/activity'),
        fetch('/api/stats')
      ])
      if (mbRes.ok) setMailboxes(await mbRes.json())
      if (alRes.ok) setAliases(await alRes.json())
      if (actRes.ok) setActivity(await actRes.json())
      if (stRes.ok) setStats(await stRes.json())
    } catch {}
  }

  useEffect(() => { fetchData() }, [])

  const handleCreateMailbox = async (e) => {
    e.preventDefault()
    if (newMailbox.password.length < 6) { showToast('Пароль минимум 6 символов', 'error'); return }
    if (stats.total_mailboxes >= MAX_MAILBOXES) { showToast(`Лимит ${MAX_MAILBOXES} ящиков достигнут`, 'error'); return }
    try {
      const res = await fetch('/api/mailboxes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newMailbox)
      })
      const data = await res.json()
      if (data.success) {
        const email = `${newMailbox.username}@${DOMAIN}`
        savePassword(email, newMailbox.password)
        setCreatedAccount({ email, password: newMailbox.password })
        setNewMailbox({ username: '', password: '', display_name: '' })
        setShowCreateMailbox(false)
        fetchData()
      } else {
        showToast(data.error || 'Ошибка создания', 'error')
      }
    } catch { showToast('Ошибка сервера', 'error') }
  }

  const handleDeleteMailbox = async (email) => {
    if (!confirm(`Точно удалить ${email}? Это нельзя отменить!`)) return
    try {
      const res = await fetch(`/api/mailboxes/${encodeURIComponent(email)}`, { method: 'DELETE' })
      const data = await res.json()
      if (data.success) removePassword(email)
      showToast(data.success ? `${email} удалён` : 'Ошибка', data.success ? 'success' : 'error')
      fetchData()
    } catch { showToast('Ошибка', 'error') }
  }

  const handleToggleMailbox = async (email) => {
    try {
      await fetch(`/api/mailboxes/${encodeURIComponent(email)}/toggle`, { method: 'POST' })
      fetchData()
    } catch {}
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (newPassword.length < 6) { showToast('Пароль минимум 6 символов', 'error'); return }
    try {
      const res = await fetch('/api/mailboxes/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: selectedEmail, new_password: newPassword })
      })
      const data = await res.json()
      if (data.success) savePassword(selectedEmail, newPassword)
      showToast(data.success ? 'Пароль изменён' : 'Ошибка', data.success ? 'success' : 'error')
      setNewPassword('')
      setShowPasswordModal(false)
    } catch { showToast('Ошибка', 'error') }
  }

  const handleCreateAlias = async (e) => {
    e.preventDefault()
    try {
      const res = await fetch('/api/aliases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newAlias)
      })
      const data = await res.json()
      if (data.success) {
        showToast('Алиас создан!')
        setNewAlias({ source: '', destination: '' })
        setShowCreateAlias(false)
        fetchData()
      } else { showToast(data.error || 'Ошибка', 'error') }
    } catch { showToast('Ошибка', 'error') }
  }

  const handleDeleteAlias = async (id) => {
    if (!confirm('Удалить алиас?')) return
    await fetch(`/api/aliases/${id}`, { method: 'DELETE' })
    fetchData()
  }

  const openPasswordModal = (email) => {
    setSelectedEmail(email)
    setNewPassword('')
    setShowPasswordModal(true)
  }

  const generateUsername = () => {
    const adj = ['fast','cool','red','big','top','neo','pro','ace','max','sky','zen','arc','hex','ion','jet','lynx','nova','onyx','bolt','flux']
    const nouns = ['mail','box','hub','dev','net','user','node','core','bit','dot','link','ping','byte','wave','star','dash','edge','sync','code','data']
    const a = adj[Math.floor(Math.random() * adj.length)]
    const n = nouns[Math.floor(Math.random() * nouns.length)]
    const num = Math.floor(Math.random() * 900) + 100
    return `${a}${n}${num}`
  }

  const generatePassword = () => {
    const chars = 'abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789!@#$%'
    let pass = ''
    for (let i = 0; i < 14; i++) pass += chars[Math.floor(Math.random() * chars.length)]
    return pass
  }

  const handleAutoGenerate = async () => {
    if (stats.total_mailboxes >= MAX_MAILBOXES) { showToast(`Лимит ${MAX_MAILBOXES} ящиков`, 'error'); return }
    const username = generateUsername()
    const password = generatePassword()
    try {
      const res = await fetch('/api/mailboxes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, display_name: '' })
      })
      const data = await res.json()
      if (data.success) {
        const email = `${username}@${DOMAIN}`
        savePassword(email, password)
        setCreatedAccount({ email, password })
        fetchData()
      } else {
        showToast(data.error || 'Ошибка', 'error')
      }
    } catch { showToast('Ошибка', 'error') }
  }

  const handleQuickCreate = async (e) => {
    e.preventDefault()
    const form = new FormData(e.target)
    const username = form.get('username')
    const password = form.get('password')
    const display_name = form.get('display_name') || ''
    if (password.length < 6) { showToast('Пароль минимум 6 символов', 'error'); return }
    if (stats.total_mailboxes >= MAX_MAILBOXES) { showToast(`Лимит ${MAX_MAILBOXES} ящиков`, 'error'); return }
    try {
      const res = await fetch('/api/mailboxes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, display_name })
      })
      const data = await res.json()
      if (data.success) {
        const email = `${username}@${DOMAIN}`
        savePassword(email, password)
        setCreatedAccount({ email, password })
        e.target.reset()
        fetchData()
      } else {
        showToast(data.error || 'Ошибка', 'error')
      }
    } catch { showToast('Ошибка', 'error') }
  }

  const remaining = MAX_MAILBOXES - stats.total_mailboxes
  const usagePercent = Math.min((stats.total_mailboxes / MAX_MAILBOXES) * 100, 100)

  return (
    <>
      <Navbar active="dashboard" />
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      <div className="dashboard container">
        <div className="page-header">
          <div>
            <h2>Панель управления</h2>
            <p className="text-muted"><span className="pulse"></span>&nbsp;&nbsp;{DOMAIN}</p>
          </div>
        </div>

        {/* Stats */}
        <div className="stats-grid">
          <div className="card stat-card animate-in">
            <div className="stat-icon-bg"><Icon name="mail" size={28} /></div>
            <div className="stat-value">{stats.total_mailboxes}</div>
            <div className="stat-label">Почтовых ящиков</div>
          </div>
          <div className="card stat-card animate-in" style={{ animationDelay: '0.05s' }}>
            <div className="stat-icon-bg"><Icon name="check" size={28} /></div>
            <div className="stat-value">{stats.active_mailboxes}</div>
            <div className="stat-label">Активных</div>
          </div>
          <div className="card stat-card animate-in" style={{ animationDelay: '0.1s' }}>
            <div className="stat-icon-bg"><Icon name="users" size={28} /></div>
            <div className="stat-value">{remaining}</div>
            <div className="stat-label">Осталось создать</div>
          </div>
          <div className="card stat-card animate-in" style={{ animationDelay: '0.15s' }}>
            <div className="stat-icon-bg"><Icon name="shuffle" size={28} /></div>
            <div className="stat-value">{stats.total_aliases}</div>
            <div className="stat-label">Алиасов</div>
          </div>
        </div>

        {/* Limit bar */}
        <div className="card animate-in" style={{ marginBottom: 20, padding: '16px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8, fontSize: '0.82rem' }}>
            <span className="text-muted">Использовано ящиков</span>
            <span style={{ color: 'var(--text)' }}><strong>{stats.total_mailboxes}</strong> / {MAX_MAILBOXES}</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${usagePercent}%` }} />
          </div>
        </div>

        {/* Main Grid */}
        <div className="dashboard-grid">
          <div className="dashboard-main">
            {/* Tabs */}
            <div className="tabs">
              <button className={`tab ${activeTab === 'mailboxes' ? 'active' : ''}`} onClick={() => setActiveTab('mailboxes')}>
                <Icon name="mail" size={15} /> Почтовые ящики
              </button>
              <button className={`tab ${activeTab === 'aliases' ? 'active' : ''}`} onClick={() => setActiveTab('aliases')}>
                <Icon name="shuffle" size={15} /> Алиасы
              </button>
            </div>

            {/* Mailboxes */}
            {activeTab === 'mailboxes' && (
              <div className="card animate-in">
                <div className="card-header">
                  <h3><Icon name="inbox" size={18} /> Почтовые ящики</h3>
                  <button className="btn btn-primary btn-sm" onClick={() => setShowCreateMailbox(true)} disabled={remaining <= 0}>
                    <Icon name="plus" size={14} /> Создать
                  </button>
                </div>
                {mailboxes.length > 0 ? (
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr><th>Email</th><th>Статус</th><th>Создан</th><th>Действия</th></tr>
                      </thead>
                      <tbody>
                        {mailboxes.map((mb) => (
                          <tr key={mb.email}>
                            <td>
                              <div className="email-info">
                                <div className="email-avatar">{mb.email[0].toUpperCase()}</div>
                                <div>
                                  <div className="email-address">
                                    {mb.email}
                                    <button className="copy-btn" onClick={() => copyToClipboard(mb.email, showToast)} title="Копировать email">
                                      <Icon name="copy" size={12} />
                                    </button>
                                  </div>
                                  {mb.display_name && <div className="email-name">{mb.display_name}</div>}
                                </div>
                              </div>
                            </td>
                            <td>
                              <span className={`badge ${mb.is_active ? 'badge-success' : 'badge-danger'}`}>
                                {mb.is_active ? 'Активен' : 'Отключён'}
                              </span>
                            </td>
                            <td className="text-muted text-sm">{mb.created_at?.slice(0, 10) || '—'}</td>
                            <td>
                              <div className="actions-row">
                                <button className="btn btn-ghost btn-icon" onClick={() => {
                                  const pw = getSavedPasswords()[mb.email]
                                  setViewCredentials({ email: mb.email, password: pw || null })
                                }} title="Данные входа">
                                  <Icon name="inbox" size={14} />
                                </button>
                                <button className="btn btn-ghost btn-icon" onClick={() => handleToggleMailbox(mb.email)} title={mb.is_active ? 'Отключить' : 'Включить'}>
                                  <Icon name={mb.is_active ? 'pause' : 'play'} size={14} />
                                </button>
                                <button className="btn btn-ghost btn-icon" onClick={() => openPasswordModal(mb.email)} title="Сменить пароль">
                                  <Icon name="key" size={14} />
                                </button>
                                <button className="btn btn-ghost-danger btn-icon" onClick={() => handleDeleteMailbox(mb.email)} title="Удалить">
                                  <Icon name="trash" size={14} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-state">
                    <div className="empty-icon"><Icon name="inbox" size={40} /></div>
                    <h4>Пока нет почтовых ящиков</h4>
                    <p>Создай первый ящик через быстрое создание справа</p>
                  </div>
                )}
              </div>
            )}

            {/* Aliases */}
            {activeTab === 'aliases' && (
              <div className="card animate-in">
                <div className="card-header">
                  <h3><Icon name="shuffle" size={18} /> Алиасы (пересылка)</h3>
                  <button className="btn btn-primary btn-sm" onClick={() => setShowCreateAlias(true)}>
                    <Icon name="plus" size={14} /> Создать
                  </button>
                </div>
                {aliases.length > 0 ? (
                  <div className="table-wrapper">
                    <table>
                      <thead>
                        <tr><th>Откуда</th><th></th><th>Куда</th><th>Действия</th></tr>
                      </thead>
                      <tbody>
                        {aliases.map(al => (
                          <tr key={al.id}>
                            <td>
                              <strong>{al.source}</strong>
                              <button className="copy-btn" onClick={() => copyToClipboard(al.source, showToast)} title="Копировать">
                                <Icon name="copy" size={12} />
                              </button>
                            </td>
                            <td style={{ color: 'var(--accent)' }}>→</td>
                            <td>
                              {al.destination}
                              <button className="copy-btn" onClick={() => copyToClipboard(al.destination, showToast)} title="Копировать">
                                <Icon name="copy" size={12} />
                              </button>
                            </td>
                            <td>
                              <button className="btn btn-ghost-danger btn-icon" onClick={() => handleDeleteAlias(al.id)}>
                                <Icon name="trash" size={14} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty-state">
                    <div className="empty-icon"><Icon name="shuffle" size={40} /></div>
                    <h4>Нет алиасов</h4>
                    <p>Алиасы позволяют пересылать письма</p>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="dashboard-sidebar">
            {/* Quick Create */}
            <div className="card quick-create animate-in" style={{ animationDelay: '0.1s' }}>
              <h4><Icon name="zap" size={16} /> Быстрое создание</h4>
              <p className="text-muted text-sm" style={{ marginBottom: 12 }}>Осталось: {remaining} из {MAX_MAILBOXES}</p>

              <button className="btn btn-accent btn-full gen-btn" onClick={handleAutoGenerate} disabled={remaining <= 0} style={{ marginBottom: 16 }}>
                <Icon name="shuffle" size={16} /> Сгенерировать аккаунт
              </button>

              <details className="manual-create">
                <summary className="text-muted text-sm" style={{ cursor: 'pointer', marginBottom: 12 }}>Или создать вручную</summary>
                <form onSubmit={handleQuickCreate}>
                  <div className="form-group">
                    <div className="input-group">
                      <input type="text" name="username" className="form-input" placeholder="username" required pattern="[a-zA-Z0-9._-]+" />
                      <span className="input-suffix">@{DOMAIN}</span>
                    </div>
                  </div>
                  <div className="form-group">
                    <input type="text" name="display_name" className="form-input" placeholder="Имя (необязательно)" />
                  </div>
                  <div className="form-group">
                    <input type="text" name="password" className="form-input" placeholder="Пароль (мин. 6)" required minLength={6} />
                  </div>
                  <button type="submit" className="btn btn-primary btn-full" disabled={remaining <= 0}>
                    <Icon name="plus" size={14} /> Создать ящик
                  </button>
                </form>
              </details>
            </div>

            {/* Activity */}
            <div className="card animate-in" style={{ animationDelay: '0.15s' }}>
              <div className="card-header"><h3><Icon name="activity" size={18} /> Последние действия</h3></div>
              {activity.length > 0 ? (
                <ul className="activity-list">
                  {activity.slice(0, 10).map((item, i) => (
                    <li className="activity-item" key={i}>
                      <div className="activity-dot"></div>
                      <div>
                        <div className="activity-text">{item.details || item.action}</div>
                        <div className="activity-time">{item.timestamp?.slice(0, 16)}</div>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : <div className="empty-state" style={{ padding: 24 }}><p>Пока нет активности</p></div>}
            </div>

            {/* Server Info */}
            <div className="card animate-in" style={{ animationDelay: '0.2s' }}>
              <div className="card-header"><h3><Icon name="server" size={18} /> Сервер</h3></div>
              <div className="info-rows">
                <div className="info-row">
                  <span>Домен</span>
                  <strong>{DOMAIN} <button className="copy-btn" onClick={() => copyToClipboard(DOMAIN, showToast)}><Icon name="copy" size={11} /></button></strong>
                </div>
                <div className="info-row">
                  <span>IMAP</span>
                  <strong>mail.{DOMAIN}:993 <button className="copy-btn" onClick={() => copyToClipboard(`mail.${DOMAIN}`, showToast)}><Icon name="copy" size={11} /></button></strong>
                </div>
                <div className="info-row">
                  <span>SMTP</span>
                  <strong>mail.{DOMAIN}:587 <button className="copy-btn" onClick={() => copyToClipboard(`mail.${DOMAIN}`, showToast)}><Icon name="copy" size={11} /></button></strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Modal: Created Account — show credentials with copy */}
      <Modal show={!!createdAccount} onClose={() => setCreatedAccount(null)} title="Аккаунт создан">
        {createdAccount && (
          <div>
            <div className="created-success">
              <Icon name="check-circle" size={40} />
              <p>Почтовый ящик создан</p>
            </div>

            <div className="credential-row">
              <label className="form-label">Email</label>
              <div className="credential-value">
                <span>{createdAccount.email}</span>
                <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(createdAccount.email, showToast)}>
                  <Icon name="copy" size={14} /> Копировать
                </button>
              </div>
            </div>

            <div className="credential-row">
              <label className="form-label">Пароль</label>
              <div className="credential-value">
                <span>{createdAccount.password}</span>
                <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(createdAccount.password, showToast)}>
                  <Icon name="copy" size={14} /> Копировать
                </button>
              </div>
            </div>

            <div className="credential-row">
              <label className="form-label">IMAP сервер</label>
              <div className="credential-value">
                <span>mail.{DOMAIN}:993 (SSL)</span>
                <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(`mail.${DOMAIN}`, showToast)}>
                  <Icon name="copy" size={14} /> Копировать
                </button>
              </div>
            </div>

            <div className="credential-row">
              <label className="form-label">SMTP сервер</label>
              <div className="credential-value">
                <span>mail.{DOMAIN}:587 (STARTTLS)</span>
                <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(`mail.${DOMAIN}`, showToast)}>
                  <Icon name="copy" size={14} /> Копировать
                </button>
              </div>
            </div>

            <button className="btn btn-primary btn-full" style={{ marginTop: 16 }} onClick={() => {
              const text = `Email: ${createdAccount.email}\nПароль: ${createdAccount.password}\nIMAP: mail.${DOMAIN}:993 (SSL)\nSMTP: mail.${DOMAIN}:587 (STARTTLS)`
              copyToClipboard(text, showToast)
            }}>
              <Icon name="copy" size={14} /> Копировать всё
            </button>

            <button className="btn btn-ghost btn-full" style={{ marginTop: 8 }} onClick={() => setCreatedAccount(null)}>
              Закрыть
            </button>
          </div>
        )}
      </Modal>

      {/* Modal: View Credentials */}
      <Modal show={!!viewCredentials} onClose={() => setViewCredentials(null)} title="Данные входа">
        {viewCredentials && (
          <div>
            <div className="credential-row">
              <label className="form-label">Email</label>
              <div className="credential-value">
                <span>{viewCredentials.email}</span>
                <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(viewCredentials.email, showToast)}>
                  <Icon name="copy" size={14} /> Копировать
                </button>
              </div>
            </div>

            <div className="credential-row">
              <label className="form-label">Пароль</label>
              {viewCredentials.password ? (
                <div className="credential-value">
                  <span>{viewCredentials.password}</span>
                  <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(viewCredentials.password, showToast)}>
                    <Icon name="copy" size={14} /> Копировать
                  </button>
                </div>
              ) : (
                <div className="credential-value" style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  <span>Пароль не сохранён (создан до установки панели)</span>
                </div>
              )}
            </div>

            <div className="credential-row">
              <label className="form-label">IMAP сервер</label>
              <div className="credential-value">
                <span>mail.{DOMAIN}:993 (SSL)</span>
                <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(`mail.${DOMAIN}`, showToast)}>
                  <Icon name="copy" size={14} /> Копировать
                </button>
              </div>
            </div>

            <div className="credential-row">
              <label className="form-label">SMTP сервер</label>
              <div className="credential-value">
                <span>mail.{DOMAIN}:587 (STARTTLS)</span>
                <button className="btn btn-ghost btn-sm" onClick={() => copyToClipboard(`mail.${DOMAIN}`, showToast)}>
                  <Icon name="copy" size={14} /> Копировать
                </button>
              </div>
            </div>

            {viewCredentials.password && (
              <button className="btn btn-primary btn-full" style={{ marginTop: 16 }} onClick={() => {
                const text = `Email: ${viewCredentials.email}\nПароль: ${viewCredentials.password}\nIMAP: mail.${DOMAIN}:993 (SSL)\nSMTP: mail.${DOMAIN}:587 (STARTTLS)`
                copyToClipboard(text, showToast)
              }}>
                <Icon name="copy" size={14} /> Копировать всё
              </button>
            )}

            <button className="btn btn-ghost btn-full" style={{ marginTop: 8 }} onClick={() => setViewCredentials(null)}>
              Закрыть
            </button>
          </div>
        )}
      </Modal>

      {/* Modal: Create Mailbox */}
      <Modal show={showCreateMailbox} onClose={() => setShowCreateMailbox(false)} title="Создать почтовый ящик">
        <form onSubmit={handleCreateMailbox}>
          <div className="form-group">
            <label className="form-label">Email адрес</label>
            <div className="input-group">
              <input type="text" className="form-input" placeholder="username" required pattern="[a-zA-Z0-9._-]+"
                value={newMailbox.username} onChange={e => setNewMailbox({ ...newMailbox, username: e.target.value })} autoFocus />
              <span className="input-suffix">@{DOMAIN}</span>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Отображаемое имя</label>
            <input type="text" className="form-input" placeholder="Иван Иванов"
              value={newMailbox.display_name} onChange={e => setNewMailbox({ ...newMailbox, display_name: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Пароль</label>
            <input type="text" className="form-input" placeholder="Минимум 6 символов" required minLength={6}
              value={newMailbox.password} onChange={e => setNewMailbox({ ...newMailbox, password: e.target.value })} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setShowCreateMailbox(false)}>Отмена</button>
            <button type="submit" className="btn btn-primary"><Icon name="plus" size={14} /> Создать</button>
          </div>
        </form>
      </Modal>

      {/* Modal: Create Alias */}
      <Modal show={showCreateAlias} onClose={() => setShowCreateAlias(false)} title="Создать алиас">
        <form onSubmit={handleCreateAlias}>
          <div className="form-group">
            <label className="form-label">Откуда (алиас)</label>
            <div className="input-group">
              <input type="text" className="form-input" placeholder="info" required
                value={newAlias.source} onChange={e => setNewAlias({ ...newAlias, source: e.target.value })} autoFocus />
              <span className="input-suffix">@{DOMAIN}</span>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Куда (получатель)</label>
            <input type="email" className="form-input" placeholder="user@komarnitsky.wiki" required
              value={newAlias.destination} onChange={e => setNewAlias({ ...newAlias, destination: e.target.value })} />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setShowCreateAlias(false)}>Отмена</button>
            <button type="submit" className="btn btn-primary"><Icon name="plus" size={14} /> Создать</button>
          </div>
        </form>
      </Modal>

      {/* Modal: Change Password */}
      <Modal show={showPasswordModal} onClose={() => setShowPasswordModal(false)} title="Сменить пароль">
        <form onSubmit={handleChangePassword}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input type="text" className="form-input" value={selectedEmail} readOnly style={{ opacity: 0.7 }} />
          </div>
          <div className="form-group">
            <label className="form-label">Новый пароль</label>
            <input type="text" className="form-input" placeholder="Минимум 6 символов" required minLength={6}
              value={newPassword} onChange={e => setNewPassword(e.target.value)} autoFocus />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={() => setShowPasswordModal(false)}>Отмена</button>
            <button type="submit" className="btn btn-primary"><Icon name="key" size={14} /> Сменить</button>
          </div>
        </form>
      </Modal>
    </>
  )
}
