import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

_, o, _ = ssh.exec_command('docker images ghcr.io/midnighttwo/wiki-panel:latest --format "{{.ID}}"', timeout=10)
old_id = o.read().decode().strip()
print(f'Current image ID: {old_id}')

for i in range(20):
    time.sleep(20)
    _, o, _ = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -3', timeout=120)
    out = o.read().decode().strip()
    print(f'[{i+1}] {out}')
    if 'Downloaded newer image' in out:
        break

# Restart
_, _, e = ssh.exec_command('cd /opt/wiki && docker compose up -d panel 2>&1', timeout=60)
print(f'\nRestart: {e.read().decode().strip()}')

time.sleep(5)

# Find actual JS file
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 ls /app/frontend/dist/assets/', timeout=10)
assets = o.read().decode().strip()
print(f'\nAssets: {assets}')

for fname in assets.split('\n'):
    fname = fname.strip()
    if fname.endswith('.js'):
        _, o, _ = ssh.exec_command(f'docker exec wiki-panel-1 grep -c "account-select" /app/frontend/dist/assets/{fname}', timeout=10)
        print(f'account-select in {fname}: {o.read().decode().strip()}')

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "admin_mail" /app/webapp/app.py', timeout=10)
print(f'admin mail in app.py: {o.read().decode().strip()}')

ssh.close()
print('\nDONE')
