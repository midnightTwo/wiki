import os
import json
import imaplib
import email
import email.header
import email.utils
import sqlite3
import secrets
import ssl
import random
import subprocess
import threading
import time
import uuid
import requests as http_requests
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

# Secondary (backup) IMAP server — RU
SECONDARY_IMAP_HOST = os.environ.get('SECONDARY_IMAP_HOST', '')
SECONDARY_IMAP_PORT = int(os.environ.get('SECONDARY_IMAP_PORT', '993'))

# Worker pool for background jobs (limited to avoid overloading server)
worker_pool = ThreadPoolExecutor(max_workers=3)

# IMAP fetch pool — parallel server queries
imap_pool = ThreadPoolExecutor(max_workers=4)

# Simple TTL cache for mail listings (avoids redundant IMAP fetches)
_mail_cache = {}  # key -> (timestamp, data)
_mail_cache_lock = threading.Lock()
MAIL_CACHE_TTL = 15  # seconds

def _cache_get(key):
    with _mail_cache_lock:
        entry = _mail_cache.get(key)
        if entry and (time.time() - entry[0]) < MAIL_CACHE_TTL:
            return entry[1]
    return None

def _cache_set(key, data):
    with _mail_cache_lock:
        _mail_cache[key] = (time.time(), data)
        # Evict old entries
        if len(_mail_cache) > 200:
            cutoff = time.time() - MAIL_CACHE_TTL * 2
            to_del = [k for k, (t, _) in _mail_cache.items() if t < cutoff]
            for k in to_del:
                del _mail_cache[k]

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
    db.execute('''CREATE TABLE IF NOT EXISTS outlook_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        recovery_email TEXT DEFAULT '',
        recovery_password TEXT DEFAULT '',
        refresh_token TEXT NOT NULL,
        client_id TEXT NOT NULL,
        tags TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )''')
    # Add tags column to outlook_accounts if missing (migration)
    try:
        db.execute('ALTER TABLE outlook_accounts ADD COLUMN tags TEXT NOT NULL DEFAULT \'{}\'') 
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


def _connect_imap(host, port):
    """Connect to an IMAP server. For external servers, skip cert verification."""
    if host in ('imap', 'localhost', '127.0.0.1'):
        # Local Docker — plain IMAP (port 143)
        return imaplib.IMAP4(host, 143)
    else:
        # External server — use plain IMAP for non-standard ports (socat proxy),
        # SSL with no cert check for standard ports
        if port not in (993, 143):
            return imaplib.IMAP4(host, port)
        elif port == 143:
            return imaplib.IMAP4(host, port)
        else:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return imaplib.IMAP4_SSL(host, port, ssl_context=ctx)


def _get_imap_servers():
    """Return list of (server_tag, host, port) for all configured IMAP servers."""
    servers = [('eu', IMAP_HOST, IMAP_PORT)]
    if SECONDARY_IMAP_HOST:
        servers.append(('ru', SECONDARY_IMAP_HOST, SECONDARY_IMAP_PORT))
    return servers


def verify_imap_login(email_addr, password):
    for tag, host, port in _get_imap_servers():
        try:
            imap = _connect_imap(host, port)
            imap.login(email_addr, password)
            imap.logout()
            return True
        except Exception:
            continue
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

    # Check if this is an Outlook account stored in DB
    is_outlook = False
    db = get_db()
    outlook_row = db.execute(
        'SELECT email, password, refresh_token, client_id FROM outlook_accounts WHERE email = ?',
        (email_addr,)
    ).fetchone()
    db.close()

    if outlook_row and outlook_row['password'] == password:
        # Outlook account — verify by getting an access token
        try:
            _outlook_get_access_token(outlook_row['refresh_token'], outlook_row['client_id'], email_addr)
            is_outlook = True
        except Exception:
            # Token failed but password matched DB — still allow login
            is_outlook = True
    elif not verify_imap_login(email_addr, password):
        return jsonify({'error': 'Wrong email or password'}), 401

    is_admin = email_addr == f'admin@{DOMAIN}'

    session['user'] = email_addr
    session['password'] = password
    session['is_admin'] = is_admin
    session['is_outlook'] = is_outlook

    return jsonify({
        'ok': True,
        'email': email_addr,
        'is_admin': is_admin,
        'is_outlook': is_outlook
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
        'is_admin': session.get('is_admin', False),
        'is_outlook': session.get('is_outlook', False)
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


def _fetch_from_one_server(server_tag, host, port, user_email, user_password):
    """Fetch mail from a single IMAP server. Returns list of messages."""
    messages = []
    try:
        imap = _connect_imap(host, port)
        imap.login(user_email, user_password)

        for folder in ['INBOX', 'Junk']:
            try:
                status, _ = imap.select(folder, readonly=True)
                if status != 'OK':
                    continue
                _, data = imap.search(None, 'ALL')
                ids = data[0].split()
                for mid in reversed(ids[-100:]):
                    _, msg_data = imap.fetch(mid, '(BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE MESSAGE-ID)] FLAGS)')
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
                        'id': f'{server_tag}:{folder}:{mid.decode()}',
                        'folder': folder,
                        'from': decode_header_value(msg.get('From', '')),
                        'to': decode_header_value(msg.get('To', '')),
                        'subject': decode_header_value(msg.get('Subject', '(no subject)')),
                        'date': date_fmt,
                        'timestamp': date_ts,
                        'seen': is_seen,
                        'spam': folder == 'Junk',
                        'server': server_tag,
                        'message_id': msg.get('Message-ID', '')
                    })
            except Exception:
                continue

        imap.logout()
    except Exception:
        pass
    return messages


def _fetch_mail(user_email, user_password):
    # Check cache first
    cache_key = f'mail:{user_email}'
    cached = _cache_get(cache_key)
    if cached is not None:
        return jsonify({'messages': cached})

    servers = _get_imap_servers()

    # Fetch from all servers in PARALLEL
    futures = []
    for server_tag, host, port in servers:
        futures.append(imap_pool.submit(_fetch_from_one_server, server_tag, host, port, user_email, user_password))

    all_messages = []
    seen_message_ids = set()
    for future in as_completed(futures):
        for msg in future.result():
            msg_id = msg.pop('message_id', '')
            if msg_id and msg_id in seen_message_ids:
                continue
            if msg_id:
                seen_message_ids.add(msg_id)
            all_messages.append(msg)

    if not all_messages and not SECONDARY_IMAP_HOST:
        return jsonify({'error': 'Cannot connect to mail server'}), 500

    all_messages.sort(key=lambda m: m['timestamp'], reverse=True)
    _cache_set(cache_key, all_messages)
    return jsonify({'messages': all_messages})


@app.route('/api/mail/<path:mail_id>')
@login_required
def api_mail_detail(mail_id):
    return _fetch_mail_detail(mail_id, session['user'], session['password'])


def _parse_mail_id(mail_id):
    """Parse mail_id: supports 'server:folder:mid' and legacy 'folder:mid'."""
    parts = mail_id.split(':')
    if len(parts) >= 3 and parts[0] in ('eu', 'ru'):
        return parts[0], parts[1], parts[2]
    # Legacy format: folder:mid (assume eu)
    return 'eu', parts[0], parts[1] if len(parts) > 1 else ''


def _get_imap_for_server(server_tag):
    """Get (host, port) for a given server tag."""
    if server_tag == 'ru' and SECONDARY_IMAP_HOST:
        return SECONDARY_IMAP_HOST, SECONDARY_IMAP_PORT
    return IMAP_HOST, IMAP_PORT


def _fetch_mail_detail(mail_id, user_email, user_password):
    try:
        server_tag, folder, mid = _parse_mail_id(mail_id)
        host, port = _get_imap_for_server(server_tag)

        imap = _connect_imap(host, port)
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
        server_tag, folder, mid = _parse_mail_id(mail_id)
        host, port = _get_imap_for_server(server_tag)

        imap = _connect_imap(host, port)
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
        # Insert '--' before the last argument (password) for 'user' and 'password'
        # commands so passwords starting with '-' aren't treated as flags
        if cmd and cmd[0] in ('user', 'password') and len(cmd) >= 3:
            cmd = cmd[:-1] + ['--', cmd[-1]]
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


# --- Outlook Accounts ---

@app.route('/api/admin/outlook/accounts')
@login_required
def api_admin_outlook_accounts():
    db = get_db()
    rows = db.execute(
        'SELECT id, email, password, recovery_email, recovery_password, refresh_token, client_id, tags, created_at '
        'FROM outlook_accounts ORDER BY id DESC'
    ).fetchall()
    db.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d['tags'] = json.loads(d.get('tags') or '{}')
        except Exception:
            d['tags'] = {}
        result.append(d)
    return jsonify({'accounts': result})


@app.route('/api/admin/outlook/tags', methods=['POST'])
@login_required
def api_admin_outlook_tags():
    data = request.get_json()
    email_addr = (data.get('email') or '').strip()
    tags = data.get('tags', {})
    if not email_addr:
        return jsonify({'error': 'Email required'}), 400
    db = get_db()
    db.execute('UPDATE outlook_accounts SET tags = ? WHERE email = ?', (json.dumps(tags), email_addr))
    db.commit()
    db.close()
    return jsonify({'ok': True})


@app.route('/api/admin/outlook/upload', methods=['POST'])
@admin_required
def api_admin_outlook_upload():
    """Bulk upload outlook accounts.
    Format per line: email:password:recovery_email:recovery_password:refresh_token:client_id
    Some lines may have extra fields at the end (ignored).
    recovery_email and recovery_password are optional (can be missing).
    Minimum: email:password:refresh_token:client_id (4 fields)
    Full: email:password:recovery_email:recovery_password:refresh_token:client_id (6 fields)
    """
    data = request.get_json()
    lines_text = (data.get('text') or '').strip()
    if not lines_text:
        return jsonify({'error': 'No data provided'}), 400

    lines = [l.strip() for l in lines_text.splitlines() if l.strip()]
    added = 0
    skipped = 0
    errors = []

    db = get_db()
    for line in lines:
        parts = line.split(':')
        if len(parts) < 4:
            errors.append(f'Too few fields: {line[:60]}...')
            continue

        # Detect format by checking if parts look like email fields
        # Full format (6+): email:password:recovery_email:recovery_password:refresh_token:client_id
        # Short format (4): email:password:refresh_token:client_id
        email_addr = parts[0].strip()
        password = parts[1].strip()

        if '@' not in email_addr:
            errors.append(f'Invalid email: {email_addr}')
            continue

        if len(parts) >= 6:
            # Full format: email:pass:recovery_email:recovery_pass:refresh_token:client_id
            recovery_email = parts[2].strip()
            recovery_password = parts[3].strip()
            refresh_token = parts[4].strip()
            client_id = parts[5].strip()
        elif len(parts) >= 4:
            # Short format: email:pass:refresh_token:client_id
            recovery_email = ''
            recovery_password = ''
            refresh_token = parts[2].strip()
            client_id = parts[3].strip()
        else:
            errors.append(f'Cannot parse: {line[:60]}...')
            continue

        if not refresh_token or not client_id:
            errors.append(f'Missing token/client_id for {email_addr}')
            continue

        try:
            db.execute(
                'INSERT OR REPLACE INTO outlook_accounts '
                '(email, password, recovery_email, recovery_password, refresh_token, client_id) '
                'VALUES (?, ?, ?, ?, ?, ?)',
                (email_addr, password, recovery_email, recovery_password, refresh_token, client_id)
            )
            added += 1
        except Exception as e:
            skipped += 1
            errors.append(f'DB error for {email_addr}: {str(e)}')

    db.commit()
    db.close()
    return jsonify({'ok': True, 'added': added, 'skipped': skipped, 'errors': errors})


@app.route('/api/admin/outlook/delete', methods=['POST'])
@login_required
def api_admin_outlook_delete():
    data = request.get_json()
    email_addr = (data.get('email') or '').strip()
    emails = data.get('emails', [])

    if emails:
        to_delete = [e.strip() for e in emails if e.strip()]
    elif email_addr:
        to_delete = [email_addr]
    else:
        return jsonify({'error': 'Email required'}), 400

    db = get_db()
    for addr in to_delete:
        db.execute('DELETE FROM outlook_accounts WHERE email = ?', (addr,))
    db.commit()
    db.close()
    return jsonify({'ok': True, 'deleted': len(to_delete)})


# OAuth2 token cache: {email: {token, expires_at}}
_token_cache = {}
_token_cache_lock = threading.Lock()

def _outlook_get_access_token(refresh_token, client_id, email_addr=''):
    """Get OAuth2 access token from Microsoft using refresh token. Cached for ~50 min."""
    cache_key = email_addr or refresh_token[:20]
    with _token_cache_lock:
        cached = _token_cache.get(cache_key)
        if cached and cached['expires_at'] > time.time():
            return cached['token']

    r = http_requests.post(
        'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        data={
            'client_id': client_id,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': 'https://outlook.office.com/IMAP.AccessAsUser.All offline_access',
        },
        timeout=15
    )
    data = r.json()
    access_token = data.get('access_token')
    if not access_token:
        error = data.get('error_description', data.get('error', 'Unknown error'))
        raise Exception(f'Cannot get access_token: {error}')

    # Cache token for 50 minutes (they last ~60 min)
    with _token_cache_lock:
        _token_cache[cache_key] = {'token': access_token, 'expires_at': time.time() + 3000}

    # Update refresh_token if Microsoft returned a new one
    new_refresh = data.get('refresh_token')
    if new_refresh and new_refresh != refresh_token:
        try:
            db = get_db()
            db.execute('UPDATE outlook_accounts SET refresh_token = ? WHERE email = ?', (new_refresh, email_addr))
            db.commit()
            db.close()
        except Exception:
            pass

    return access_token


def _outlook_imap_connect(email_addr, access_token):
    """Connect to Outlook IMAP using OAuth2."""
    auth_string = f'user={email_addr}\x01auth=Bearer {access_token}\x01\x01'
    imap = imaplib.IMAP4_SSL('outlook.office365.com')
    imap.authenticate('XOAUTH2', lambda _: auth_string.encode())
    return imap


@app.route('/api/admin/outlook/mail')
@login_required
def api_admin_outlook_mail():
    account = request.args.get('account', '').strip()
    if not account:
        return jsonify({'error': 'account param required'}), 400

    db = get_db()
    row = db.execute(
        'SELECT refresh_token, client_id FROM outlook_accounts WHERE email = ?',
        (account,)
    ).fetchone()
    db.close()

    if not row:
        return jsonify({'error': 'Account not found'}), 404

    try:
        access_token = _outlook_get_access_token(row['refresh_token'], row['client_id'], account)
        imap = _outlook_imap_connect(account, access_token)

        messages = []
        for folder in ['INBOX', 'Junk']:
            try:
                status, _ = imap.select(folder, readonly=True)
                if status != 'OK':
                    continue
                _, data = imap.search(None, 'ALL')
                ids = data[0].split()
                # Only fetch last 30 messages (not 100) for speed
                batch = list(reversed(ids[-30:]))
                if not batch:
                    continue
                # Fetch only headers + flags (not full RFC822) for the list
                id_set = b','.join(batch)
                _, fetch_data = imap.fetch(id_set, '(FLAGS BODY.PEEK[HEADER.FIELDS (FROM TO SUBJECT DATE)])')
                # Parse response pairs
                i = 0
                while i < len(fetch_data):
                    item = fetch_data[i]
                    if isinstance(item, tuple) and len(item) == 2:
                        meta_line = item[0].decode() if isinstance(item[0], bytes) else str(item[0])
                        header_bytes = item[1] if isinstance(item[1], bytes) else b''
                        # Extract message ID from response
                        import re as _re
                        mid_match = _re.search(r'^(\d+)', meta_line)
                        mid_str = mid_match.group(1) if mid_match else '0'
                        is_seen = '\\Seen' in meta_line
                        # Parse header
                        msg = email.message_from_bytes(header_bytes)
                        date_str = msg.get('Date', '')
                        try:
                            date_parsed = email.utils.parsedate_to_datetime(date_str)
                            date_fmt = date_parsed.strftime('%d.%m.%Y %H:%M')
                            date_ts = date_parsed.timestamp()
                        except Exception:
                            date_fmt = date_str[:20] if date_str else ''
                            date_ts = 0
                        messages.append({
                            'id': f'{folder}:{mid_str}',
                            'folder': folder,
                            'from': decode_header_value(msg.get('From', '')),
                            'to': decode_header_value(msg.get('To', '')),
                            'subject': decode_header_value(msg.get('Subject', '(no subject)')),
                            'date': date_fmt,
                            'timestamp': date_ts,
                            'seen': is_seen,
                            'spam': folder == 'Junk'
                        })
                    i += 1
            except Exception:
                continue

        imap.logout()
        messages.sort(key=lambda m: m['timestamp'], reverse=True)
        return jsonify({'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/outlook/mail/<path:mail_id>')
@login_required
def api_admin_outlook_mail_detail(mail_id):
    account = request.args.get('account', '').strip()
    if not account:
        return jsonify({'error': 'account param required'}), 400

    db = get_db()
    row = db.execute(
        'SELECT refresh_token, client_id FROM outlook_accounts WHERE email = ?',
        (account,)
    ).fetchone()
    db.close()

    if not row:
        return jsonify({'error': 'Account not found'}), 404

    try:
        parts = mail_id.split(':')
        folder = parts[0]
        mid = parts[1]

        access_token = _outlook_get_access_token(row['refresh_token'], row['client_id'], account)
        imap = _outlook_imap_connect(account, access_token)
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


# --- SPA ---

@app.route('/')
@app.route('/<path:path>')
def serve_spa(path=''):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        resp = send_from_directory(app.static_folder, path)
    else:
        resp = send_from_directory(app.static_folder, 'index.html')
    if path == '' or path.endswith('.html'):
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return resp


if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=8000, debug=True)
