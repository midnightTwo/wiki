import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# First check what's in the current container
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 head -5 /app/webapp/app.py', timeout=10)
print(f'Current app.py head: {o.read().decode().strip()}')

# Force pull
print('\nPulling latest...')
_, o, _ = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -3', timeout=120)
print(o.read().decode().strip())

# Recreate
_, _, e = ssh.exec_command('cd /opt/wiki && docker compose up -d --force-recreate panel 2>&1', timeout=60)
print(f'\n{e.read().decode().strip()}')

time.sleep(5)

# Verify
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "html_body" /app/webapp/app.py', timeout=10)
print(f'\nhtml_body count: {o.read().decode().strip()}')

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "wrapHtml" /app/frontend/dist/assets/*.js 2>/dev/null || echo 0', timeout=10)
res = o.read().decode().strip()
print(f'wrapHtml in JS: {res}')

# If not found, list JS files
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 ls /app/frontend/dist/assets/', timeout=10)
assets = o.read().decode().strip()
print(f'Assets: {assets}')

for f in assets.split('\n'):
    f = f.strip()
    if f.endswith('.js'):
        _, o, _ = ssh.exec_command(f'docker exec wiki-panel-1 grep -c "wrapHtml" /app/frontend/dist/assets/{f}', timeout=10)
        print(f'  wrapHtml in {f}: {o.read().decode().strip()}')

ssh.close()
print('\nDONE')
