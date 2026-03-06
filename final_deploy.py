import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Force pull with digest
print('Force pulling...')
_, o, _ = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1', timeout=120)
print(o.read().decode().strip())

# Restart panel
print('\nRestarting...')
_, _, e = ssh.exec_command('cd /opt/wiki && docker compose up -d panel 2>&1', timeout=60)
stderr = e.read().decode().strip()
print(stderr)

time.sleep(5)

# Check
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 ls /app/frontend/dist/assets/', timeout=10)
assets = o.read().decode().strip()
print(f'\nAssets: {assets}')

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "admin/mail" /app/webapp/app.py', timeout=10)
print(f'admin/mail routes in app.py: {o.read().decode().strip()}')

for f in assets.split('\n'):
    f = f.strip()
    if f.endswith('.js'):
        _, o, _ = ssh.exec_command(f'docker exec wiki-panel-1 grep -c "account-select" /app/frontend/dist/assets/{f}', timeout=10)
        print(f'account-select in {f}: {o.read().decode().strip()}')

ssh.close()
print('\nDONE')
