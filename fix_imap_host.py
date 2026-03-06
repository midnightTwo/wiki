import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

cmds = [
    # Add IMAP_HOST to panel environment in docker-compose.yml on server
    r"""sed -i '/- MAIL_DOMAIN=kmr-mail.online/a\      - IMAP_HOST=imap' /opt/wiki/docker-compose.yml""",
    # Verify
    "grep -A5 'environment' /opt/wiki/docker-compose.yml | tail -10",
    # Restart just the panel
    "cd /opt/wiki && docker compose up -d panel",
]

for cmd in cmds:
    print(f'\n>>> {cmd}')
    _, o, e = ssh.exec_command(cmd, timeout=60)
    print(o.read().decode())
    err = e.read().decode()
    if err:
        print(f'STDERR: {err}')

time.sleep(5)

# Test IMAP connectivity from panel
print('\n>>> Testing IMAP from panel...')
imap_test = '''docker exec wiki-panel-1 python3 -c "
import imaplib
try:
    m = imaplib.IMAP4('imap', 143, timeout=10)
    print('Connected to imap:143')
    r = m.login('admin@kmr-mail.online', 'himarra228')
    print(f'Login: {r}')
    m.logout()
except Exception as e:
    print(f'Error: {e}')
"'''
_, o, e = ssh.exec_command(imap_test, timeout=30)
print(o.read().decode())
err = e.read().decode()
if err:
    print(f'STDERR: {err}')

ssh.close()
print('\nDONE')
