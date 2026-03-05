import { useState } from 'react'
import { DOMAIN } from '../App'
import Navbar from '../components/Navbar'
import Toast from '../components/Toast'
import { Icon } from '../components/Icons'

export default function Settings() {
  const [toast, setToast] = useState(null)
  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' })

  const showToast = (message, type = 'success') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (form.new_password !== form.confirm_password) {
      showToast('Пароли не совпадают', 'error')
      return
    }
    if (form.new_password.length < 6) {
      showToast('Минимум 6 символов', 'error')
      return
    }
    try {
      const res = await fetch('/api/settings/password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      })
      const data = await res.json()
      showToast(data.success ? 'Пароль админки изменён!' : (data.error || 'Ошибка'), data.success ? 'success' : 'error')
      if (data.success) setForm({ current_password: '', new_password: '', confirm_password: '' })
    } catch {
      showToast('Ошибка сервера', 'error')
    }
  }

  return (
    <>
      <Navbar active="settings" />
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}

      <div className="dashboard container">
        <div className="page-header">
          <div>
            <h2><Icon name="settings" size={24} /> Настройки</h2>
            <p className="text-muted">Управление параметрами админки</p>
          </div>
        </div>

        <div style={{ maxWidth: 600 }}>
          <div className="card animate-in" style={{ marginBottom: 24 }}>
            <div className="card-header"><h3><Icon name="lock" size={18} /> Пароль админки</h3></div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Текущий пароль</label>
                <input type="password" className="form-input" required value={form.current_password}
                  onChange={e => setForm({ ...form, current_password: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Новый пароль</label>
                <input type="password" className="form-input" required minLength={6} value={form.new_password}
                  onChange={e => setForm({ ...form, new_password: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label">Подтверждение пароля</label>
                <input type="password" className="form-input" required minLength={6} value={form.confirm_password}
                  onChange={e => setForm({ ...form, confirm_password: e.target.value })} />
              </div>
              <button type="submit" className="btn btn-primary"><Icon name="lock" size={14} /> Сменить пароль</button>
            </form>
          </div>

          <div className="card animate-in" style={{ marginBottom: 24, animationDelay: '0.05s' }}>
            <div className="card-header"><h3><Icon name="server" size={18} /> Информация о сервере</h3></div>
            <div className="info-rows">
              <div className="info-row"><span>Домен</span><strong>{DOMAIN}</strong></div>
              <div className="info-row"><span>Почтовый хост</span><strong>mail.{DOMAIN}</strong></div>
              <div className="info-row"><span>IMAP</span><strong>mail.{DOMAIN}:993</strong></div>
              <div className="info-row"><span>SMTP</span><strong>mail.{DOMAIN}:587</strong></div>
            </div>
          </div>

          <div className="card animate-in" style={{ animationDelay: '0.1s' }}>
            <div className="card-header"><h3><Icon name="link" size={18} /> Полезные ссылки</h3></div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <a href={`https://mxtoolbox.com/?domain=${DOMAIN}`} target="_blank" className="btn btn-ghost btn-full" style={{ justifyContent: 'flex-start' }}>
                <Icon name="search" size={15} /> Проверить MX записи
              </a>
              <a href="https://mail-tester.com" target="_blank" className="btn btn-ghost btn-full" style={{ justifyContent: 'flex-start' }}>
                <Icon name="activity" size={15} /> Тест доставляемости писем
              </a>
              <a href={`https://www.ssllabs.com/ssltest/analyze.html?d=mail.${DOMAIN}`} target="_blank" className="btn btn-ghost btn-full" style={{ justifyContent: 'flex-start' }}>
                <Icon name="shield" size={15} /> Проверить SSL сертификат
              </a>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
