import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Pull latest image
print('Pulling latest image...')
_, o, e = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -3', timeout=120)
out = o.read().decode().strip()
print(out)

if 'Downloaded newer image' in out:
    print('New image found, restarting...')
    _, o, e = ssh.exec_command('cd /opt/wiki && docker compose up -d panel 2>&1', timeout=60)
    print(e.read().decode())
    time.sleep(5)

# Verify
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "account-select" /app/frontend/dist/assets/*.js 2>/dev/null || echo NOT_FOUND', timeout=10)
print(f'account-select in JS: {o.read().decode().strip()}')

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "api_admin_mail" /app/webapp/app.py 2>/dev/null || echo NOT_FOUND', timeout=10)
print(f'admin mail routes: {o.read().decode().strip()}')

ssh.close()
print('DONE')
