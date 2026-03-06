import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2')

# Get mail list for ee244156 via admin API (inside container)
cmd = """docker exec wiki-panel-1 python3 -c "
import imaplib, email

IMAP_HOST = 'imap'
user = 'ee244156@kmr-mail.online'
pw = 'bGmVDPwUXMzp4A'

imap = imaplib.IMAP4(IMAP_HOST, 143)
imap.login(user, pw)
imap.select('INBOX')
_, nums = imap.search(None, 'ALL')
ids = nums[0].split()
if ids:
    mid = ids[-1]
    _, data = imap.fetch(mid, '(RFC822)')
    raw = data[0][1]
    msg = email.message_from_bytes(raw)
    
    # same logic as get_email_body
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
        print('BODY_TYPE: html')
        print('HTML_LEN:', len(html_body))
        print('HAS_HTML_TAG:', '<html' in html_body.lower())
        print('HAS_IMG:', '<img' in html_body.lower())
        print('FIRST_500:', html_body[:500])
    elif text_body:
        print('BODY_TYPE: text')
        print('TEXT_LEN:', len(text_body))
    else:
        print('BODY_TYPE: none')
imap.logout()
"
"""

_, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print("ERR:", err)
ssh.close()
