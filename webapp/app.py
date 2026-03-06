import os
import json
import imaplib
import email
import email.header
import email.utils
import sqlite3
import secrets
import subprocess
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

DOMAIN = os.environ.get('MAIL_DOMAIN', 'kmr-mail.online')
IMAP_HOST = os.environ.get('IMAP_HOST', 'imap')
IMAP_PORT = int(os.environ.get('IMAP_PORT', '993'))
ADMIN_CONTAINER = os.environ.get('ADMIN_CONTAINER', 'wiki-admin-1')
DB_PATH = os.environ.get('DB_PATH', '/data/panel.db')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'himarra228')


# --- Database ---

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS generated_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )''')
    # Add tags column if missing (migration)
    try:
        db.execute('ALTER TABLE generated_accounts ADD COLUMN tags TEXT NOT NULL DEFAULT \'{}\'')
    except Exception:
        pass
    db.commit()
    db.close()


# --- Auth ---

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session or not session.get('is_admin'):
            return jsonify({'error': 'Forbidden'}), 403
        return f(*args, **kwargs)
    return decorated


def verify_imap_login(email_addr, password):
    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        imap.login(email_addr, password)
        imap.logout()
        return True
    except imaplib.IMAP4.error:
        return False
    except Exception:
        try:
            imap = imaplib.IMAP4(IMAP_HOST, 143)
            imap.login(email_addr, password)
            imap.logout()
            return True
        except Exception:
            return False


# --- API Routes ---

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data'}), 400

    email_addr = (data.get('email') or '').strip()
    password = data.get('password', '')

    if not email_addr or not password:
        return jsonify({'error': 'Email and password required'}), 400

    if '@' not in email_addr:
        email_addr = f'{email_addr}@{DOMAIN}'

    if not verify_imap_login(email_addr, password):
        return jsonify({'error': 'Wrong email or password'}), 401

    is_admin = email_addr == f'admin@{DOMAIN}'

    session['user'] = email_addr
    session['password'] = password
    session['is_admin'] = is_admin

    return jsonify({
        'ok': True,
        'email': email_addr,
        'is_admin': is_admin
    })


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/me')
@login_required
def api_me():
    return jsonify({
        'email': session['user'],
        'is_admin': session.get('is_admin', False)
    })


# --- Mail ---

def decode_header_value(val):
    if not val:
        return ''
    decoded = email.header.decode_header(val)
    parts = []
    for text, charset in decoded:
        if isinstance(text, bytes):
            parts.append(text.decode(charset or 'utf-8', errors='replace'))
        else:
            parts.append(text)
    return ''.join(parts)


def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == 'text/html':
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                return payload.decode(charset, errors='replace'), 'html'
            if ct == 'text/plain':
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                return payload.decode(charset, errors='replace'), 'text'
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or 'utf-8'
        ct = msg.get_content_type()
        return payload.decode(charset, errors='replace'), 'html' if 'html' in ct else 'text'
    return '', 'text'


@app.route('/api/admin/mail')
@admin_required
def api_admin_mail():
    """Admin reads any user's mailbox"""
    account = request.args.get('account', '').strip()
    if not account:
        return jsonify({'error': 'account param required'}), 400
    db = get_db()
    row = db.execute('SELECT password FROM generated_accounts WHERE email = ?', (account,)).fetchone()
    db.close()
    if account == f'admin@{DOMAIN}':
        acc_password = session['password']
    elif row:
        acc_password = row['password']
    else:
        return jsonify({'error': 'Account not found'}), 404
    return _fetch_mail(account, acc_password)


@app.route('/api/admin/mail/<path:mail_id>')
@admin_required
def api_admin_mail_detail(mail_id):
    account = request.args.get('account', '').strip()
    if not account:
        return jsonify({'error': 'account param required'}), 400
    db = get_db()
    row = db.execute('SELECT password FROM generated_accounts WHERE email = ?', (account,)).fetchone()
    db.close()
    if account == f'admin@{DOMAIN}':
        acc_password = session['password']
    elif row:
        acc_password = row['password']
    else:
        return jsonify({'error': 'Account not found'}), 404
    return _fetch_mail_detail(mail_id, account, acc_password)


@app.route('/api/admin/mail/<path:mail_id>', methods=['DELETE'])
@admin_required
def api_admin_mail_delete(mail_id):
    account = request.args.get('account', '').strip()
    if not account:
        return jsonify({'error': 'account param required'}), 400
    db = get_db()
    row = db.execute('SELECT password FROM generated_accounts WHERE email = ?', (account,)).fetchone()
    db.close()
    if account == f'admin@{DOMAIN}':
        acc_password = session['password']
    elif row:
        acc_password = row['password']
    else:
        return jsonify({'error': 'Account not found'}), 404
    return _delete_mail(mail_id, account, acc_password)


@app.route('/api/mail')
@login_required
def api_mail():
    return _fetch_mail(session['user'], session['password'])


def _fetch_mail(user_email, user_password):
    try:
        try:
            imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        except Exception:
            imap = imaplib.IMAP4(IMAP_HOST, 143)
        imap.login(user_email, user_password)

        messages = []

        for folder in ['INBOX', 'Junk']:
            try:
                status, _ = imap.select(folder, readonly=True)
                if status != 'OK':
                    continue
                _, data = imap.search(None, 'ALL')
                ids = data[0].split()
                for mid in reversed(ids[-100:]):
                    _, msg_data = imap.fetch(mid, '(RFC822 FLAGS)')
                    raw = msg_data[0][1]
                    msg = email.message_from_bytes(raw)

                    flags_raw = msg_data[0][0].decode() if msg_data[0][0] else ''
                    is_seen = '\\Seen' in flags_raw

                    date_str = msg.get('Date', '')
                    try:
                        date_parsed = email.utils.parsedate_to_datetime(date_str)
                        date_fmt = date_parsed.strftime('%d.%m.%Y %H:%M')
                        date_ts = date_parsed.timestamp()
                    except Exception:
                        date_fmt = date_str[:20]
                        date_ts = 0

                    messages.append({
                        'id': f'{folder}:{mid.decode()}',
                        'folder': folder,
                        'from': decode_header_value(msg.get('From', '')),
                        'to': decode_header_value(msg.get('To', '')),
                        'subject': decode_header_value(msg.get('Subject', '(no subject)')),
                        'date': date_fmt,
                        'timestamp': date_ts,
                        'seen': is_seen,
                        'spam': folder == 'Junk'
                    })
            except Exception:
                continue

        imap.logout()

        messages.sort(key=lambda m: m['timestamp'], reverse=True)
        return jsonify({'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mail/<path:mail_id>')
@login_required
def api_mail_detail(mail_id):
    return _fetch_mail_detail(mail_id, session['user'], session['password'])


def _fetch_mail_detail(mail_id, user_email, user_password):
    try:
        parts = mail_id.split(':')
        folder = parts[0]
        mid = parts[1]

        try:
            imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        except Exception:
            imap = imaplib.IMAP4(IMAP_HOST, 143)
        imap.login(user_email, user_password)
        imap.select(folder)
        _, msg_data = imap.fetch(mid.encode(), '(RFC822)')
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        body, body_type = get_email_body(msg)

        imap.logout()

        return jsonify({
            'from': decode_header_value(msg.get('From', '')),
            'to': decode_header_value(msg.get('To', '')),
            'subject': decode_header_value(msg.get('Subject', '')),
            'date': decode_header_value(msg.get('Date', '')),
            'body': body,
            'body_type': body_type
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _delete_mail(mail_id, user_email, user_password):
    try:
        parts = mail_id.split(':')
        folder = parts[0]
        mid = parts[1]

        try:
            imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        except Exception:
            imap = imaplib.IMAP4(IMAP_HOST, 143)
        imap.login(user_email, user_password)
        imap.select(folder)
        imap.store(mid.encode(), '+FLAGS', '\\Deleted')
        imap.expunge()
        imap.logout()

        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# --- Admin: Account Management ---

def mailu_command(cmd):
    try:
        result = subprocess.run(
            ['docker', 'exec', ADMIN_CONTAINER, 'flask', 'mailu'] + cmd,
            capture_output=True, text=True, timeout=30
        )
        return result.stdout + result.stderr
    except Exception as e:
        return str(e)


@app.route('/api/admin/accounts')
@admin_required
def api_admin_accounts():
    db = get_db()
    accounts = db.execute(
        'SELECT email, password, tags, created_at FROM generated_accounts ORDER BY id DESC'
    ).fetchall()
    db.close()
    result = []
    for a in accounts:
        d = dict(a)
        try:
            d['tags'] = json.loads(d.get('tags') or '{}')
        except Exception:
            d['tags'] = {}
        result.append(d)
    return jsonify({'accounts': result})


@app.route('/api/admin/tags', methods=['POST'])
@admin_required
def api_admin_tags():
    data = request.get_json()
    email_addr = (data.get('email') or '').strip()
    tags = data.get('tags', {})
    if not email_addr:
        return jsonify({'error': 'Email required'}), 400
    db = get_db()
    db.execute('UPDATE generated_accounts SET tags = ? WHERE email = ?',
               (json.dumps(tags), email_addr))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/admin/create', methods=['POST'])
@admin_required
def api_admin_create():
    data = request.get_json()
    username = (data.get('username') or '').strip()
    password = data.get('password', '')

    if not username:
        return jsonify({'error': 'Username required'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': 'Password min 6 chars'}), 400

    email_addr = f'{username}@{DOMAIN}'
    result = mailu_command(['user', username, DOMAIN, password])

    if 'exists' in result.lower():
        return jsonify({'error': f'{email_addr} already exists'}), 409

    db = get_db()
    try:
        db.execute(
            'INSERT INTO generated_accounts (email, password) VALUES (?, ?)',
            (email_addr, password)
        )
        db.commit()
    except sqlite3.IntegrityError:
        pass
    db.close()

    return jsonify({'ok': True, 'email': email_addr, 'password': password})


@app.route('/api/admin/generate', methods=['POST'])
@admin_required
def api_admin_generate():
    data = request.get_json() or {}
    count = min(int(data.get('count', 1)), 50)

    created = []
    for _ in range(count):
        username = secrets.token_hex(4)
        password = secrets.token_urlsafe(10)
        email_addr = f'{username}@{DOMAIN}'

        result = mailu_command(['user', username, DOMAIN, password])
        if 'exists' in result.lower():
            continue

        db = get_db()
        try:
            db.execute(
                'INSERT INTO generated_accounts (email, password) VALUES (?, ?)',
                (email_addr, password)
            )
            db.commit()
        except sqlite3.IntegrityError:
            pass
        db.close()

        created.append({'email': email_addr, 'password': password})

    return jsonify({'ok': True, 'created': created})


@app.route('/api/admin/delete', methods=['POST'])
@admin_required
def api_admin_delete():
    data = request.get_json()
    email_addr = (data.get('email') or '').strip()
    if not email_addr:
        return jsonify({'error': 'Email required'}), 400

    parts = email_addr.split('@')
    if len(parts) != 2:
        return jsonify({'error': 'Invalid email'}), 400

    if email_addr == f'admin@{DOMAIN}':
        return jsonify({'error': 'Cannot delete admin'}), 403

    mailu_command(['user-delete', parts[0] + '@' + parts[1]])

    db = get_db()
    db.execute('DELETE FROM generated_accounts WHERE email = ?', (email_addr,))
    db.commit()
    db.close()

    return jsonify({'ok': True})


# --- SPA ---

@app.route('/')
@app.route('/<path:path>')
def serve_spa(path=''):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)
