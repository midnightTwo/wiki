import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

script = '''
import imaplib, email

imap = imaplib.IMAP4("imap", 143, timeout=10)
imap.login("e3498859@kmr-mail.online", "3I7tw6Ob2aJO2A")
imap.select("INBOX")
_, data = imap.search(None, "ALL")
ids = data[0].split()
print(f"Total emails: {len(ids)}")
for mid in ids[-3:]:
    _, msg_data = imap.fetch(mid, "(RFC822)")
    raw = msg_data[0][1]
    msg = email.message_from_bytes(raw)
    subj = msg.get("Subject", "?")[:50]
    ct = msg.get_content_type()
    multi = msg.is_multipart()
    print(f"\\nMID {mid.decode()}: {subj}")
    print(f"  Content-Type: {ct}, multipart: {multi}")
    if multi:
        has_html = False
        has_text = False
        for part in msg.walk():
            pct = part.get_content_type()
            disp = part.get_content_disposition()
            if pct == "text/html" and disp != "attachment":
                has_html = True
                p = part.get_payload(decode=True)
                cs = part.get_content_charset() or "utf-8"
                h = p.decode(cs, errors="replace")
                print(f"  HTML part: {len(h)} chars, preview: {h[:150]}")
            elif pct == "text/plain" and disp != "attachment":
                has_text = True
        print(f"  has_html={has_html}, has_text={has_text}")
    else:
        p = msg.get_payload(decode=True)
        if p:
            cs = msg.get_content_charset() or "utf-8"
            b = p.decode(cs, errors="replace")
            print(f"  Body: {len(b)} chars, preview: {b[:150]}")
imap.logout()
'''

_, o, e = ssh.exec_command(f'docker exec wiki-panel-1 python3 -c "{script}"', timeout=30)
print(o.read().decode())
err = e.read().decode()
if err:
    print(f'ERR: {err}')
ssh.close()
