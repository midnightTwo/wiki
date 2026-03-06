import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Check panel logs after login attempt
print('=== Panel logs ===')
_, o, e = ssh.exec_command('docker logs wiki-panel-1 --tail 30 2>&1', timeout=15)
print(o.read().decode())

# Test IMAP directly from panel container
print('=== Test IMAP from panel container ===')
imap_test = """docker exec wiki-panel-1 python3 -c "
import imaplib
print('Testing IMAP SSL on 192.168.203.8:993...')
try:
    m = imaplib.IMAP4_SSL('192.168.203.8', 993, timeout=10)
    print('SSL connected')
    r = m.login('admin@kmr-mail.online', 'himarra228')
    print(f'Login result: {r}')
    m.logout()
except Exception as e:
    print(f'SSL failed: {e}')

print('Testing IMAP plain on 192.168.203.8:143...')
try:
    m = imaplib.IMAP4('192.168.203.8', 143, timeout=10)
    print('Plain connected')
    r = m.login('admin@kmr-mail.online', 'himarra228')
    print(f'Login result: {r}')
    m.logout()
except Exception as e:
    print(f'Plain failed: {e}')
"
"""
_, o, e = ssh.exec_command(imap_test, timeout=30)
print(o.read().decode())
err = e.read().decode()
if err:
    print(f'STDERR: {err}')

# Check network connectivity
print('=== Network check ===')
_, o, e = ssh.exec_command('docker exec wiki-panel-1 python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect((\'192.168.203.8\', 143)); print(\'Port 143 OK\'); s.close()"', timeout=15)
print(o.read().decode())
err = e.read().decode()
if err:
    print(f'STDERR: {err}')

# Check if panel is on the right network
print('=== Panel network ===')
_, o, e = ssh.exec_command("docker inspect wiki-panel-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'", timeout=10)
print(f'Panel IP: {o.read().decode().strip()}')

_, o, e = ssh.exec_command("docker inspect wiki-imap-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}'", timeout=10)
print(f'IMAP IP: {o.read().decode().strip()}')

ssh.close()
print('\nDONE')
