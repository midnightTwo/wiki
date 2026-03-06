import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('195.66.114.73', username='root', password='b7uLZ6oHb5A2', timeout=30, banner_timeout=30)

# Get current image digest
_, o, _ = ssh.exec_command('docker images ghcr.io/midnighttwo/wiki-panel:latest --format "{{.ID}}"', timeout=10)
old_id = o.read().decode().strip()
print(f'Current image: {old_id}')

# Wait and pull until new image arrives
for i in range(24):
    print(f'\nAttempt {i+1}, waiting 15s...')
    time.sleep(15)
    _, o, _ = ssh.exec_command('docker pull ghcr.io/midnighttwo/wiki-panel:latest 2>&1 | tail -3', timeout=60)
    out = o.read().decode().strip()
    print(out)
    
    if 'Downloaded newer image' in out:
        print('NEW IMAGE FOUND!')
        break
    if i > 15:
        print('Giving up')
        break

# Restart panel
print('\nRestarting panel...')
_, o, e = ssh.exec_command('cd /opt/wiki && docker compose up -d panel', timeout=60)
print(e.read().decode())

time.sleep(5)

# Verify new code
_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c refresh-btn /app/frontend/dist/assets/*.js 2>/dev/null || echo 0', timeout=10)
print(f'refresh-btn in JS: {o.read().decode().strip()}')

_, o, _ = ssh.exec_command('docker exec wiki-panel-1 grep -c "api_mail_delete" /app/webapp/app.py 2>/dev/null || echo 0', timeout=10)
print(f'DELETE endpoint in app.py: {o.read().decode().strip()}')

ssh.close()
print('\nDONE')
