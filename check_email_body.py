import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Check if new app.py is deployed (should have html_body)
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "html_body" /app/webapp/app.py', timeout=10)
print(f'html_body in app.py: {o.read().decode().strip()}')

# Test fetching a real email to see what body_type is returned
test_code = r"""
import imaplib, email, json

imap = imaplib.IMAP4('imap', 143, timeout=10)
imap.login('e3498859@kmr-mail.online', '3I7tw6Ob2aJO2A')
imap.select('INBOX')
_, data = imap.search(None, 'ALL')
ids = data[0].split()
if ids:
    mid = ids[-1]
    _, msg_data = imap.fetch(mid, '(RFC822)')
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)
    print(f'Content-Type: {msg.get_content_type()}')
    print(f'Is multipart: {msg.is_multipart()}')
    if msg.is_multipart():
        for i, part in enumerate(msg.walk()):
            ct = part.get_content_type()
            disp = part.get_content_disposition()
            print(f'  Part {i}: {ct} (disp={disp})')
            if ct == 'text/html':
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or 'utf-8'
                html = payload.decode(charset, errors='replace')
                print(f'  HTML length: {len(html)}')
                print(f'  HTML preview: {html[:300]}')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            body = payload.decode(charset, errors='replace')
            print(f'Body length: {len(body)}')
            print(f'Body preview: {body[:200]}')
else:
    print('No emails')
imap.logout()
"""

_, o, e = ssh.exec_command(f'docker exec wiki-panel-1 python3 -c {json.dumps(test_code)}', timeout=30)
print(o.read().decode())
err = e.read().decode()
if err:
    print(f'STDERR: {err}')

ssh.close()
print('DONE')
