import paramiko, time, urllib.request, urllib.parse, json, http.cookiejar

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Wait for IMAP to be healthy
print('Waiting for IMAP to be healthy...')
for i in range(12):
    _, o, _ = ssh.exec_command('docker inspect wiki-imap-1 --format "{{.State.Health.Status}}"', timeout=10)
    status = o.read().decode().strip()
    print(f'  IMAP status: {status}')
    if status == 'healthy':
        break
    time.sleep(5)

# Reset admin password
print('\nResetting admin password...')
_, o, e = ssh.exec_command('docker exec wiki-admin-1 flask mailu password admin kmr-mail.online himarra228', timeout=30)
print(o.read().decode())
print(e.read().decode())

ssh.close()

# Test login via API
print('\nTesting login via API...')
time.sleep(3)
try:
    data = json.dumps({'email': 'admin@kmr-mail.online', 'password': 'himarra228'}).encode()
    req = urllib.request.Request(
        'http://kmr-mail.online:8000/api/login',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req, timeout=15)
    print(f'Status: {resp.status}')
    print(f'Response: {resp.read().decode()}')
except urllib.error.HTTPError as e:
    print(f'HTTP Error: {e.code}')
    print(f'Response: {e.read().decode()}')
except Exception as e:
    print(f'Error: {e}')

print('\nDONE')
