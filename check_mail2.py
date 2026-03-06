import paramiko, os, tempfile

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

script = '''import imaplib, email
imap = imaplib.IMAP4("imap", 143, timeout=10)
imap.login("e3498859@kmr-mail.online", "3I7tw6Ob2aJO2A")
imap.select("INBOX")
_, data = imap.search(None, "ALL")
ids = data[0].split()
print("Total:", len(ids))
for mid in ids[-3:]:
    _, msg_data = imap.fetch(mid, "(RFC822)")
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)
    subj = msg.get("Subject", "?")[:50]
    print("\\n---", mid.decode(), subj)
    print("CT:", msg.get_content_type(), "multi:", msg.is_multipart())
    if msg.is_multipart():
        for part in msg.walk():
            pct = part.get_content_type()
            disp = part.get_content_disposition()
            if pct in ("text/html", "text/plain") and disp != "attachment":
                p = part.get_payload(decode=True)
                cs = part.get_content_charset() or "utf-8"
                b = p.decode(cs, errors="replace")
                print(f"  {pct}: {len(b)} chars")
                if pct == "text/html":
                    print("  preview:", b[:200])
    else:
        p = msg.get_payload(decode=True)
        if p:
            cs = msg.get_content_charset() or "utf-8"
            b = p.decode(cs, errors="replace")
            print(f"  body ({msg.get_content_type()}): {len(b)} chars")
            print("  preview:", b[:200])
imap.logout()
'''

# Copy script into container and run
sftp = ssh.open_sftp()
sftp.open('/tmp/check_mail.py', 'w').write(script)
sftp.close()

_, o, e = ssh.exec_command('docker cp /tmp/check_mail.py wiki-panel-1:/tmp/check_mail.py && docker exec wiki-panel-1 python3 /tmp/check_mail.py', timeout=30)
print(o.read().decode())
err = e.read().decode()
if err:
    print(f'ERR: {err}')
ssh.close()
