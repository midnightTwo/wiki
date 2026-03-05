"""
Komarnitsky Mail — API Backend
Flask JSON API для React фронтенда
Пароль админки: himarra228
"""

import os
import subprocess
import hashlib
import secrets
import sqlite3
from datetime import timedelta
from functools import wraps

from flask import Flask, request, jsonify, session, g, send_from_directory

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)

# ---- Config ----
ADMIN_PASSWORD_HASH = hashlib.sha256('himarra228'.encode()).hexdigest()
DOMAIN = os.environ.get('MAIL_DOMAIN', 'komarnitsky.wiki')
DB_PATH = os.environ.get('DB_PATH', os.path.join(os.path.dirname(__file__), 'mail.db'))


# ---- Database ----
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else '.', exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.execute('''CREATE TABLE IF NOT EXISTS mailboxes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL,
        display_name TEXT DEFAULT '', quota INTEGER DEFAULT 1073741824,
        is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT (datetime('now')),
        last_login TEXT, messages_received INTEGER DEFAULT 0, messages_sent INTEGER DEFAULT 0
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS aliases (
        id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT NOT NULL,
        destination TEXT NOT NULL, is_active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT (datetime('now'))
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
        details TEXT, timestamp TEXT DEFAULT (datetime('now'))
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    db.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password_hash', ?)", (ADMIN_PASSWORD_HASH,))
    db.commit()
    db.close()


def log_activity(action, details=None):
    try:
        db = get_db()
        db.execute('INSERT INTO activity_log (action, details) VALUES (?, ?)', (action, details))
        db.commit()
    except Exception:
        pass


# ---- Mailu Docker ----
def mailu_command(cmd_args):
    try:
        full_cmd = ['docker', 'compose', '-f', '/mailu/docker-compose.yml',
                     'exec', '-T', 'admin', 'flask', 'mailu'] + cmd_args
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, '', str(e)


# ---- Auth ----
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def get_admin_hash():
    try:
        db = get_db()
        row = db.execute("SELECT value FROM settings WHERE key='admin_password_hash'").fetchone()
        return row['value'] if row else ADMIN_PASSWORD_HASH
    except Exception:
        return ADMIN_PASSWORD_HASH


# =====================================================
# API — Auth
# =====================================================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    pw_hash = hashlib.sha256(data.get('password', '').encode()).hexdigest()
    if pw_hash == get_admin_hash():
        session['logged_in'] = True
        session.permanent = True
        log_activity('login', 'Успешный вход в админку')
        return jsonify({'success': True})
    log_activity('login_failed', 'Неудачная попытка входа')
    return jsonify({'success': False, 'error': 'Неверный пароль'}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})


# =====================================================
# API — Stats
# =====================================================
@app.route('/api/stats')
@login_required
def api_stats():
    db = get_db()
    return jsonify({
        'total_mailboxes': db.execute('SELECT COUNT(*) as c FROM mailboxes').fetchone()['c'],
        'active_mailboxes': db.execute('SELECT COUNT(*) as c FROM mailboxes WHERE is_active=1').fetchone()['c'],
        'total_aliases': db.execute('SELECT COUNT(*) as c FROM aliases').fetchone()['c'],
        'domain': DOMAIN
    })


# =====================================================
# API — Mailboxes
# =====================================================
@app.route('/api/mailboxes')
@login_required
def api_get_mailboxes():
    db = get_db()
    return jsonify([dict(r) for r in db.execute('SELECT * FROM mailboxes ORDER BY created_at DESC').fetchall()])


@app.route('/api/mailboxes', methods=['POST'])
@login_required
def api_create_mailbox():
    data = request.get_json()
    username = data.get('username', '').strip().lower()
    password = data.get('password', '')
    display_name = data.get('display_name', '').strip()

    if not username:
        return jsonify({'success': False, 'error': 'Введи имя'}), 400
    if not password or len(password) < 6:
        return jsonify({'success': False, 'error': 'Пароль минимум 6 символов'}), 400

    clean = username.replace('.', '').replace('-', '').replace('_', '')
    if not clean.isalnum():
        return jsonify({'success': False, 'error': 'Только буквы, цифры, точки, дефисы'}), 400

    email = f'{username}@{DOMAIN}'
    mailu_command(['user', username, DOMAIN, password])

    db = get_db()
    try:
        db.execute('INSERT INTO mailboxes (email, display_name) VALUES (?, ?)', (email, display_name))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': f'{email} уже существует'}), 409

    log_activity('create_mailbox', f'Создан ящик {email}')
    return jsonify({'success': True, 'email': email})


@app.route('/api/mailboxes/<path:email>', methods=['DELETE'])
@login_required
def api_delete_mailbox(email):
    mailu_command(['user-delete', email])
    db = get_db()
    db.execute('DELETE FROM mailboxes WHERE email = ?', (email,))
    db.commit()
    log_activity('delete_mailbox', f'Удалён ящик {email}')
    return jsonify({'success': True})


@app.route('/api/mailboxes/<path:email>/toggle', methods=['POST'])
@login_required
def api_toggle_mailbox(email):
    db = get_db()
    mb = db.execute('SELECT * FROM mailboxes WHERE email = ?', (email,)).fetchone()
    if not mb:
        return jsonify({'success': False}), 404
    new_status = 0 if mb['is_active'] else 1
    db.execute('UPDATE mailboxes SET is_active = ? WHERE email = ?', (new_status, email))
    db.commit()
    log_activity('toggle_mailbox', f'{email} {"активирован" if new_status else "деактивирован"}')
    return jsonify({'success': True, 'is_active': new_status})


@app.route('/api/mailboxes/password', methods=['POST'])
@login_required
def api_change_password():
    data = request.get_json()
    email = data.get('email', '')
    new_password = data.get('new_password', '')
    if len(new_password) < 6:
        return jsonify({'success': False, 'error': 'Минимум 6 символов'}), 400
    mailu_command(['password', email.split('@')[0], DOMAIN, new_password])
    log_activity('change_password', f'Сменён пароль для {email}')
    return jsonify({'success': True})


# =====================================================
# API — Aliases
# =====================================================
@app.route('/api/aliases')
@login_required
def api_get_aliases():
    db = get_db()
    return jsonify([dict(r) for r in db.execute('SELECT * FROM aliases ORDER BY created_at DESC').fetchall()])


@app.route('/api/aliases', methods=['POST'])
@login_required
def api_create_alias():
    data = request.get_json()
    source = data.get('source', '').strip().lower()
    destination = data.get('destination', '').strip().lower()
    if not source or not destination:
        return jsonify({'success': False, 'error': 'Заполни оба поля'}), 400
    if '@' not in source:
        source = f'{source}@{DOMAIN}'
    db = get_db()
    db.execute('INSERT INTO aliases (source, destination) VALUES (?, ?)', (source, destination))
    db.commit()
    mailu_command(['alias', source.split('@')[0], DOMAIN, destination])
    log_activity('create_alias', f'Алиас {source} → {destination}')
    return jsonify({'success': True})


@app.route('/api/aliases/<int:alias_id>', methods=['DELETE'])
@login_required
def api_delete_alias(alias_id):
    db = get_db()
    alias = db.execute('SELECT * FROM aliases WHERE id = ?', (alias_id,)).fetchone()
    if alias:
        db.execute('DELETE FROM aliases WHERE id = ?', (alias_id,))
        db.commit()
        log_activity('delete_alias', f'Удалён алиас {alias["source"]}')
    return jsonify({'success': True})


# =====================================================
# API — Activity
# =====================================================
@app.route('/api/activity')
@login_required
def api_activity():
    db = get_db()
    return jsonify([dict(r) for r in db.execute('SELECT * FROM activity_log ORDER BY timestamp DESC LIMIT 30').fetchall()])


# =====================================================
# API — Settings
# =====================================================
@app.route('/api/settings/password', methods=['POST'])
@login_required
def api_change_admin_password():
    data = request.get_json()
    current_hash = hashlib.sha256(data.get('current_password', '').encode()).hexdigest()
    if current_hash != get_admin_hash():
        return jsonify({'success': False, 'error': 'Текущий пароль неверный'}), 403
    new_pw = data.get('new_password', '')
    if new_pw != data.get('confirm_password', ''):
        return jsonify({'success': False, 'error': 'Пароли не совпадают'}), 400
    if len(new_pw) < 6:
        return jsonify({'success': False, 'error': 'Минимум 6 символов'}), 400
    db = get_db()
    db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('admin_password_hash', ?)",
               (hashlib.sha256(new_pw.encode()).hexdigest(),))
    db.commit()
    log_activity('change_admin_password', 'Пароль админки изменён')
    return jsonify({'success': True})


# =====================================================
# Serve React SPA
# =====================================================
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=os.environ.get('DEBUG', False))
