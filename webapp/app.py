import os
import json
import imaplib
import email
import email.header
import email.utils
import sqlite3
import secrets
import random
import subprocess
import threading
import time
import uuid
from datetime import datetime
from functools import wraps
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, request, jsonify, send_from_directory, session

app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

DOMAIN = os.environ.get('MAIL_DOMAIN', 'kmr-mail.online')
DOMAINS = [d.strip() for d in os.environ.get('MAIL_DOMAINS', DOMAIN).split(',') if d.strip()]
IMAP_HOST = os.environ.get('IMAP_HOST', 'imap')
IMAP_PORT = int(os.environ.get('IMAP_PORT', '993'))
ADMIN_CONTAINER = os.environ.get('ADMIN_CONTAINER', 'wiki-admin-1')
DB_PATH = os.environ.get('DB_PATH', '/data/panel.db')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'himarra228')

# Worker pool for background jobs (limited to avoid overloading server)
worker_pool = ThreadPoolExecutor(max_workers=3)

# Background jobs tracking
jobs = {}  # job_id -> {status, total, done, created, errors}
jobs_lock = threading.Lock()


# --- Realistic Username Generator ---

_FIRST_NAMES = [
    'alex', 'ivan', 'maks', 'denis', 'artem', 'nikita', 'dima', 'kirill',
    'roma', 'vlad', 'andrey', 'sergey', 'pavel', 'oleg', 'igor', 'sasha',
    'kolya', 'vanya', 'kostya', 'misha', 'petya', 'vitya', 'zhenya', 'grisha',
    'timur', 'ruslan', 'danil', 'egor', 'ilya', 'mark', 'lev', 'gleb',
    'fedor', 'matvey', 'stepan', 'bogdan', 'yaroslav', 'dmitry', 'anton',
    'maxim', 'valera', 'slava', 'tolik', 'gena', 'borya', 'yura', 'lyosha',
    'tema', 'arseniy', 'savva', 'platon', 'mir', 'leon', 'alan', 'eldar',
    'tima', 'amir', 'robert', 'adam', 'david', 'renat', 'kamil', 'bulat',
    'arina', 'masha', 'dasha', 'katya', 'nastya', 'sveta', 'olya', 'lena',
    'tanya', 'anya', 'polina', 'alina', 'vika', 'marina', 'liza', 'sonya',
    'kira', 'vera', 'nika', 'milana', 'sofiya', 'ulyana', 'valeriya', 'ksenia',
    'eva', 'diana', 'alisa', 'rita', 'ira', 'natasha', 'galya', 'nadya',
    'yulia', 'ksusha', 'zina', 'lara', 'nina', 'alla', 'emma', 'maya',
    'zlata', 'tamara', 'rosa', 'stella', 'mila', 'nelli', 'angelina', 'karina',
]

_LAST_PARTS = [
    'ov', 'ev', 'in', 'ko', 'uk', 'enko', 'ova', 'eva', 'ina', 'sky',
    'nov', 'kov', 'lev', 'shin', 'kin', 'lin', 'min', 'lov', 'nik', 'chuk',
    'ovich', 'enko', 'yuk', 'ak', 'an', 'ets', 'ich', 'tsov', 'chenk', 'skiy',
    'zon', 'man', 'berg', 'stein', 'feld', 'baum', 'ler', 'ner', 'son', 'sen',
]

_WORDS = [
    'pro', 'dev', 'top', 'best', 'cool', 'real', 'fast', 'smart', 'lucky', 'true',
    'fire', 'dark', 'wild', 'ice', 'neo', 'max', 'red', 'blue', 'black', 'gold',
    'sun', 'star', 'sky', 'wolf', 'fox', 'cat', 'lion', 'bear', 'hawk', 'tiger',
    'play', 'win', 'run', 'go', 'fly', 'live', 'rock', 'jazz', 'beat', 'vibe',
]


def generate_realistic_username():
    """Generate a realistic-looking username with 100k+ unique combinations."""
    pattern = random.randint(1, 10)

    name = random.choice(_FIRST_NAMES)
    last = random.choice(_LAST_PARTS)
    word = random.choice(_WORDS)
    num = random.randint(0, 999)

    if pattern == 1:
        # makskov7
        return f"{name}{last}{random.randint(0, 9)}"
    elif pattern == 2:
        # ivan.litvin
        name2 = random.choice(_FIRST_NAMES)
        sep = random.choice(['.', '_', ''])
        return f"{name}{sep}{name2}"
    elif pattern == 3:
        # artempro99
        return f"{name}{word}{random.randint(1, 99)}"
    elif pattern == 4:
        # d.komarenko
        return f"{name[0]}{random.choice(['.', '_'])}{name}{last}"
    elif pattern == 5:
        # nikita2003
        return f"{name}{random.randint(1990, 2006)}"
    elif pattern == 6:
        # smartigor
        return f"{word}{name}"
    elif pattern == 7:
        # maks_ov95
        return f"{name}_{last}{random.randint(10, 99)}"
    elif pattern == 8:
        # ivanlis9
        short_last = random.choice(_LAST_PARTS)[:3]
        return f"{name}{short_last}{random.randint(0, 9)}"
    elif pattern == 9:
        # xd.misha.fire
        prefix = random.choice(['xd', 'mr', 'xx', 'the', 'ya', 'im'])
        return f"{prefix}.{name}.{word}"
    else:
        # prodartem
        return f"{word}{name}"


def generate_realistic_password():
    """Generate a strong but memorable-looking password."""
    return secrets.token_urlsafe(12)


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
        html_body = None
        text_body = None
        for part in msg.walk():
            ct = part.get_content_type()
            if part.get_content_disposition() == 'attachment':
                continue
            if ct == 'text/html' and not html_body:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                html_body = payload.decode(charset, errors='replace')
            elif ct == 'text/plain' and not text_body:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                text_body = payload.decode(charset, errors='replace')
        if html_body:
            return html_body, 'html'
        if text_body:
            return text_body, 'text'
    else:
        payload = msg.get_payload(decode=True)
        if payload:
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

@app.route('/api/domains')
@login_required
def api_domains():
    return jsonify({'domains': DOMAINS})


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
    domain = (data.get('domain') or '').strip() or DOMAIN

    if domain not in DOMAINS:
        return jsonify({'error': f'Domain {domain} not allowed'}), 400
    if not username:
        return jsonify({'error': 'Username required'}), 400
    if not password or len(password) < 6:
        return jsonify({'error': 'Password min 6 chars'}), 400

    email_addr = f'{username}@{domain}'
    result = mailu_command(['user', username, domain, password])

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


def _create_single_account(username, domain, password):
    """Create one account in Mailu and return (email, password) or None on failure."""
    email_addr = f'{username}@{domain}'
    result = mailu_command(['user', username, domain, password])
    if 'exists' in result.lower():
        return None
    return (email_addr, password)


def _run_generate_job(job_id, count, domain):
    """Background worker: generate accounts in small parallel batches."""
    BATCH = 5  # parallel docker exec at once (don't overload Mailu)
    accounts_to_create = []
    for _ in range(count):
        for _attempt in range(5):
            username = generate_realistic_username()
            # ensure no duplicate in this batch
            if username not in [u for u, _ in accounts_to_create]:
                break
        password = generate_realistic_password()
        accounts_to_create.append((username, password))

    created = []
    errors = 0

    for i in range(0, len(accounts_to_create), BATCH):
        batch = accounts_to_create[i:i+BATCH]
        futures = {}
        with ThreadPoolExecutor(max_workers=BATCH) as batch_pool:
            for username, password in batch:
                f = batch_pool.submit(_create_single_account, username, domain, password)
                futures[f] = (username, password)

            for f in as_completed(futures):
                try:
                    result = f.result()
                    if result:
                        created.append({'email': result[0], 'password': result[1]})
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        # Save completed batch to DB
        if created:
            db = get_db()
            for acc in created[len(created) - len([f for f in futures if futures[f]])::]:
                try:
                    db.execute(
                        'INSERT INTO generated_accounts (email, password) VALUES (?, ?)',
                        (acc['email'], acc['password'])
                    )
                except sqlite3.IntegrityError:
                    pass
            db.commit()
            db.close()

        with jobs_lock:
            jobs[job_id]['done'] = min(i + BATCH, count)
            jobs[job_id]['created'] = created[:]

    # Save all to DB in one final pass (idempotent due to UNIQUE constraint)
    db = get_db()
    for acc in created:
        try:
            db.execute(
                'INSERT OR IGNORE INTO generated_accounts (email, password) VALUES (?, ?)',
                (acc['email'], acc['password'])
            )
        except Exception:
            pass
    db.commit()
    db.close()

    with jobs_lock:
        jobs[job_id]['status'] = 'done'
        jobs[job_id]['done'] = count
        jobs[job_id]['created'] = created
        jobs[job_id]['errors'] = errors


@app.route('/api/admin/generate', methods=['POST'])
@admin_required
def api_admin_generate():
    data = request.get_json() or {}
    count = min(int(data.get('count', 1)), 200)
    domain = (data.get('domain') or '').strip() or DOMAIN

    if domain not in DOMAINS:
        return jsonify({'error': f'Domain {domain} not allowed'}), 400

    # Small batches (<=5) — run synchronously for instant response
    if count <= 5:
        created = []
        for _ in range(count):
            username = generate_realistic_username()
            password = generate_realistic_password()
            result = _create_single_account(username, domain, password)
            if result:
                db = get_db()
                try:
                    db.execute(
                        'INSERT OR IGNORE INTO generated_accounts (email, password) VALUES (?, ?)',
                        (result[0], result[1])
                    )
                    db.commit()
                except Exception:
                    pass
                db.close()
                created.append({'email': result[0], 'password': result[1]})
        return jsonify({'ok': True, 'created': created})

    # Large batches — run in background
    job_id = str(uuid.uuid4())[:8]
    with jobs_lock:
        jobs[job_id] = {
            'status': 'running',
            'total': count,
            'done': 0,
            'created': [],
            'errors': 0
        }
    worker_pool.submit(_run_generate_job, job_id, count, domain)
    return jsonify({'ok': True, 'job_id': job_id})


@app.route('/api/admin/job/<job_id>')
@admin_required
def api_admin_job_status(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job not found'}), 404
    return jsonify(job)


@app.route('/api/admin/delete', methods=['POST'])
@admin_required
def api_admin_delete():
    data = request.get_json()
    email_addr = (data.get('email') or '').strip()
    emails = data.get('emails', [])

    # Support bulk delete
    if emails:
        to_delete = [e.strip() for e in emails if e.strip() and e.strip() != f'admin@{DOMAIN}']
    elif email_addr:
        if email_addr == f'admin@{DOMAIN}':
            return jsonify({'error': 'Cannot delete admin'}), 403
        to_delete = [email_addr]
    else:
        return jsonify({'error': 'Email required'}), 400

    for addr in to_delete:
        parts = addr.split('@')
        if len(parts) != 2:
            continue
        mailu_command(['user-delete', addr])

    db = get_db()
    for addr in to_delete:
        db.execute('DELETE FROM generated_accounts WHERE email = ?', (addr,))
    db.commit()
    db.close()

    return jsonify({'ok': True, 'deleted': len(to_delete)})


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
